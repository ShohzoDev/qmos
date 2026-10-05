"""Hodisalarni standartga muvofiqligini tekshirish.

Ikki bosqich:
  1) sxema (JSON Schema 2020-12) — tuzilish, turlar, majburiy maydonlar;
  2) mazmun — sxema bilan ifodalab bo'lmaydigan qoidalar (tuman kodi
     viloyatga tegishli, tugash sanasi boshlanishidan keyin, va h.k.).

Yuboruvchi (masalan BuildOps) ham, markaz ham AYNAN shu funksiyalardan
foydalanadi — shuning uchun "yuboruvchi to'g'ri deb o'ylagan, markaz rad
etgan" holati bo'lmaydi (markazdagi ma'lumotga bog'liq tekshiruvlar —
unknown_site, conflict va h.k. — bundan mustasno).
"""
import json
import uuid as _uuid
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from importlib import resources

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SXEMA_PAPKASI = 'schemas/v1'
TOSHKENT = timezone(timedelta(hours=5))
KELAJAK_CHEGARASI = timedelta(minutes=10)

_format = FormatChecker(formats=())


@_format.checks('date', raises=ValueError)
def _sana(qiymat):
    if not isinstance(qiymat, str):
        return True
    date.fromisoformat(qiymat)
    return True


@_format.checks('date-time', raises=ValueError)
def _vaqt(qiymat):
    if not isinstance(qiymat, str):
        return True
    v = datetime.fromisoformat(qiymat.replace('Z', '+00:00'))
    if v.tzinfo is None:
        raise ValueError("vaqt zonasi ko'rsatilmagan")
    return True


@_format.checks('uuid', raises=ValueError)
def _uuid_tekshir(qiymat):
    if not isinstance(qiymat, str):
        return True
    _uuid.UUID(qiymat)
    return True


@lru_cache(maxsize=None)
def sxemalar():
    """{fayl_nomi: sxema} — paket ichidagi barcha v1 sxemalar."""
    papka = resources.files('qmos').joinpath(SXEMA_PAPKASI)
    return {
        f.name: json.loads(f.read_text(encoding='utf-8'))
        for f in papka.iterdir() if f.name.endswith('.json')
    }


@lru_cache(maxsize=None)
def _registry():
    return Registry().with_resources(
        (nom, Resource.from_contents(sxema, default_specification=DRAFT202012))
        for nom, sxema in sxemalar().items()
    )


@lru_cache(maxsize=None)
def validator(nom):
    """`nom` — sxema fayli, masalan 'event.json' yoki 'batch.json'."""
    return Draft202012Validator(sxemalar()[nom], registry=_registry(), format_checker=_format)


def _pointer(qism):
    return '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in qism) if qism else ''


def _xato(code, path, message):
    return {'code': code, 'path': path, 'message': message}


def sxema_xatolari(obj, nom='event.json'):
    """Sxema xatolari ro'yxati (bo'sh — to'g'ri). Eng aniq (eng chuqur)
    xato birinchi."""
    xatolar = []
    for e in validator(nom).iter_errors(obj):
        # if/then ichidagi xatolar — eng aniq sabablarni ko'rsatamiz.
        ichki = list(e.context) if e.context else []
        for x in (ichki or [e]):
            xatolar.append(_xato('schema', _pointer(x.absolute_path), x.message))
    xatolar.sort(key=lambda x: (-x['path'].count('/'), x['path'], x['message']))
    # Takrorlarni olib tashlash (if/then bir xil xatoni ikki marta beradi).
    korilgan, natija = set(), []
    for x in xatolar:
        kalit = (x['path'], x['message'])
        if kalit not in korilgan:
            korilgan.add(kalit)
            natija.append(x)
    return natija


def _vaqt_ol(qiymat):
    return datetime.fromisoformat(qiymat.replace('Z', '+00:00'))


def mazmun_xatolari(hodisa, hozir=None):
    """Sxemadan o'tgan hodisa uchun mazmun xatolari. `hozir` berilsa —
    kelajakdagi vaqtlar ham tekshiriladi (markaz shu bilan chaqiradi)."""
    xatolar = []
    tur = hodisa['event_type']
    d = hodisa['data']
    sodir = _vaqt_ol(hodisa['occurred_at'])

    if hodisa.get('supersedes') and hodisa['supersedes'].lower() == hodisa['event_id'].lower():
        xatolar.append(_xato('semantic', '/supersedes', "Hodisa o'zini o'zi tuzata olmaydi."))
    if hozir is not None and sodir - hozir > KELAJAK_CHEGARASI:
        xatolar.append(_xato('semantic', '/occurred_at', "Vaqt kelajakda (qurilma soatini tekshiring)."))

    if tur == 'site.profile':
        manzil = d['address']
        if not manzil['district_soato'].startswith(manzil['region_soato']):
            xatolar.append(_xato('semantic', '/data/address/district_soato',
                                 "Tuman kodi ko'rsatilgan viloyatga tegishli emas."))
        if date.fromisoformat(d['planned_end']) < date.fromisoformat(d['planned_start']):
            xatolar.append(_xato('semantic', '/data/planned_end',
                                 "Tugash sanasi boshlanish sanasidan oldin."))

    elif tur == 'site.work_plan':
        xatolar += _takror_xatolari(d['items'], '/data/items')

    elif tur == 'site.daily_report':
        ish = d['workforce']
        if ish.get('verified_present', 0) > ish['present']:
            xatolar.append(_xato('semantic', '/data/workforce/verified_present',
                                 "Tasdiqlanganlar soni umumiy sondan ko'p."))
        kun = date.fromisoformat(d['date'])
        if kun > sodir.astimezone(TOSHKENT).date():
            xatolar.append(_xato('semantic', '/data/date', "Hisobot sanasi hodisa vaqtidan keyin."))
        xatolar += _takror_xatolari(d['work_done'], '/data/work_done')

    elif tur == 'site.photo':
        if _vaqt_ol(d['taken_at']) - sodir > KELAJAK_CHEGARASI:
            xatolar.append(_xato('semantic', '/data/taken_at', "Surat hodisa qayd etilganidan keyin olingan."))

    elif tur == 'site.incident':
        if _vaqt_ol(d['happened_at']) - sodir > KELAJAK_CHEGARASI:
            xatolar.append(_xato('semantic', '/data/happened_at', "Hodisa qayd etilganidan keyin sodir bo'lgan."))

    return xatolar


def _takror_xatolari(qatorlar, yol):
    xatolar, korilgan = [], set()
    for i, q in enumerate(qatorlar):
        if q['item_id'] in korilgan:
            xatolar.append(_xato('semantic', f'{yol}/{i}/item_id', f"item_id takrorlangan: {q['item_id']}"))
        korilgan.add(q['item_id'])
    return xatolar


def hodisa_xatolari(hodisa, hozir=None):
    """Bitta hodisaning barcha xatolari (avval sxema; u o'tsa — mazmun)."""
    xatolar = sxema_xatolari(hodisa, 'event.json')
    if xatolar:
        return xatolar
    return mazmun_xatolari(hodisa, hozir=hozir)


def tekshir(hodisa, hozir=None):
    """True — hodisa standartga mos."""
    return not hodisa_xatolari(hodisa, hozir=hozir)

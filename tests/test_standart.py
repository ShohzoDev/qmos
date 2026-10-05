"""QMOS standartining kontrakt testlari.

    python -m unittest discover -s tests -v

Tekshiriladi:
  1. Har bir sxema JSON Schema 2020-12 bo'yicha to'g'ri va barcha
     havolalari ochiladi.
  2. examples/v1/valid/ dagi har bir misol o'z sxemasidan va mazmun
     tekshiruvidan o'tadi.
  3. examples/v1/invalid/ dagi har bir misol AYNAN kutilgan sabab bilan
     rad etiladi (_kutilgan.json: xato kodi va JSON Pointer yo'li).
  4. Har bir hodisa turining sxemasi, to'g'ri misoli va noto'g'ri misoli
     bor — yangi tur misolsiz qo'shilsa test yiqiladi.
  5. Ma'lumotni minimallashtirish: sxemalarning birortasida ham moliya
     yoki shaxsiy ma'lumot maydoni yo'q (taqiqlangan so'zlar ro'yxati).
  6. Imzo: to'g'ri imzo o'tadi; tana, yo'l, usul, vaqt yoki kalit
     o'zgarsa — rad etiladi.
  7. docs/ (openapi.json, index.html) sxemalardan yasalgan holatga mos —
     hujjat kod bilan hech qachon farqlanmaydi.

Fayl nomi qoidasi: `<sxema>--<holat>.json` — masalan
`event--site-profile.json` event.json sxemasi bilan tekshiriladi.
"""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ))

from jsonschema import Draft202012Validator  # noqa: E402

import qmos  # noqa: E402
from qmos.imzo import imzoni_tekshir, sign_request  # noqa: E402

MISOLLAR = ILDIZ / 'examples' / 'v1'
HOZIR = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


def misollar(papka):
    return sorted(p for p in (MISOLLAR / papka).glob('*.json') if not p.name.startswith('_'))


def sxema_nomi(fayl):
    return fayl.name.split('--', 1)[0] + '.json'


def tekshir(fayl, obj):
    """Fayl turiga qarab barcha xatolar (hodisada — mazmun ham)."""
    nom = sxema_nomi(fayl)
    xatolar = qmos.sxema_xatolari(obj, nom)
    if not xatolar and nom == 'event.json':
        xatolar = qmos.mazmun_xatolari(obj, hozir=HOZIR)
    if not xatolar and nom == 'batch.json':
        for i, h in enumerate(obj['events']):
            xatolar += [dict(x, path=f'/events/{i}{x["path"]}') for x in qmos.mazmun_xatolari(h, hozir=HOZIR)]
    return xatolar


class Sxemalar(unittest.TestCase):
    def test_sxemalar_togri(self):
        for nom, s in qmos.sxemalar().items():
            with self.subTest(nom):
                Draft202012Validator.check_schema(s)

    def test_havolalar_ochiladi(self):
        # Har bir sxema bilan bo'sh obyektni tekshirish barcha $ref'larni
        # yechishga majbur qiladi; yechilmasa — istisno.
        for nom in qmos.sxemalar():
            with self.subTest(nom):
                list(qmos.validator(nom).iter_errors({}))

    def test_qatiy_obyektlar(self):
        """Har bir `properties`li obyektda additionalProperties: false —
        aks holda standartdan tashqari maydon (masalan maosh) jimgina
        o'tib ketadi."""
        def aylan(obj, yol):
            if isinstance(obj, dict):
                if 'properties' in obj and obj.get('type') == 'object':
                    self.assertIs(obj.get('additionalProperties'), False, yol)
                for k, v in obj.items():
                    aylan(v, f'{yol}/{k}')
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    aylan(v, f'{yol}/{i}')
        for nom, s in qmos.sxemalar().items():
            aylan(s, nom)


class Misollar(unittest.TestCase):
    def test_togri_misollar(self):
        fayllar = misollar('valid')
        self.assertGreaterEqual(len(fayllar), 10)
        for f in fayllar:
            with self.subTest(f.name):
                obj = json.loads(f.read_text(encoding='utf-8'))
                self.assertEqual(tekshir(f, obj), [])

    def test_notogri_misollar_kutilgan_sabab_bilan_rad_etiladi(self):
        kutilgan = json.loads((MISOLLAR / 'invalid' / '_kutilgan.json').read_text(encoding='utf-8'))
        fayllar = misollar('invalid')
        self.assertEqual(sorted(kutilgan), [f.name for f in fayllar], "_kutilgan.json fayllar bilan mos emas")
        for f in fayllar:
            with self.subTest(f.name):
                xatolar = tekshir(f, json.loads(f.read_text(encoding='utf-8')))
                self.assertTrue(xatolar, 'rad etilmadi')
                k = kutilgan[f.name]
                self.assertIn((k['code'], k['path']), [(x['code'], x['path']) for x in xatolar], xatolar)

    def test_har_bir_hodisa_turi_qamrab_olingan(self):
        turlar = qmos.sxemalar()['event.json']['properties']['event_type']['enum']
        shartlar = {b['if']['properties']['event_type']['const'] for b in qmos.sxemalar()['event.json']['allOf']}
        self.assertEqual(set(turlar), shartlar, "har bir tur uchun data sxemasi bo'lishi kerak")
        togri = {json.loads(f.read_text(encoding='utf-8'))['event_type']
                 for f in misollar('valid') if sxema_nomi(f) == 'event.json'}
        self.assertEqual(set(turlar), togri, "har bir tur uchun to'g'ri misol bo'lishi kerak")

    def test_bir_xil_event_id_yoq(self):
        idlar = [json.loads(f.read_text(encoding='utf-8'))['event_id']
                 for f in misollar('valid') if sxema_nomi(f) == 'event.json']
        self.assertEqual(len(idlar), len(set(idlar)))


class MalumotMinimal(unittest.TestCase):
    """Moliya, narx va shaxsiy ma'lumot standartga kirmasligi kerak.
    Bu ro'yxatni kengaytirish mumkin, qisqartirish — faqat ochiq qaror bilan."""
    TAQIQLI = ('salary', 'wage', 'payroll', 'price', 'cost', 'payment', 'debt', 'balance', 'cash',
               'passport', 'pinfl', 'birth', 'card', 'iban', 'account_number')

    def test_taqiqli_maydon_yoq(self):
        def kalitlar(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == 'properties':
                        yield from v.keys()
                    yield from kalitlar(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from kalitlar(v)
        for nom, s in qmos.sxemalar().items():
            for k in kalitlar(s):
                with self.subTest(sxema=nom, maydon=k):
                    self.assertFalse(any(t in k.lower() for t in self.TAQIQLI))


class Imzo(unittest.TestCase):
    KALIT, SIR, YOL = 'buildops-305123456', 'maxfiy-kalit-32-bayt-uzunlikda!!', '/v1/events'
    TANA = b'{"events":[]}'
    VAQT = 1_790_000_000

    def sarlavha(self):
        return sign_request(self.KALIT, self.SIR, 'POST', self.YOL, self.TANA, timestamp=self.VAQT)

    def tekshir(self, **kw):
        s = self.sarlavha()
        a = dict(secret=self.SIR, timestamp=s['X-QMOS-Timestamp'], method='POST', path=self.YOL,
                 tana=self.TANA, imzo=s['X-QMOS-Signature'], hozir=self.VAQT + 5)
        a.update(kw)
        return imzoni_tekshir(**a)[0]

    def test_togri_imzo(self):
        self.assertTrue(self.tekshir())
        self.assertEqual(self.sarlavha()['X-QMOS-Key-Id'], self.KALIT)

    def test_ozgarish_rad_etiladi(self):
        self.assertFalse(self.tekshir(tana=b'{"events":[1]}'))
        self.assertFalse(self.tekshir(path='/v1/media'))
        self.assertFalse(self.tekshir(method='PUT'))
        self.assertFalse(self.tekshir(secret='boshqa-kalit'))
        self.assertFalse(self.tekshir(timestamp=str(self.VAQT + 1)))
        self.assertFalse(self.tekshir(imzo='0' * 64))
        self.assertFalse(self.tekshir(timestamp='abc'))

    def test_vaqt_chegarasi(self):
        self.assertTrue(self.tekshir(hozir=self.VAQT + 300))
        self.assertFalse(self.tekshir(hozir=self.VAQT + 301))
        self.assertFalse(self.tekshir(hozir=self.VAQT - 301))

    def test_namuna_vektor(self):
        """Boshqa tillardagi (PHP, Java, C#) ilovalar shu qiymat bilan
        o'zini tekshiradi — README'da ham keltirilgan."""
        self.assertEqual(self.sarlavha()['X-QMOS-Signature'], NAMUNA_IMZO)


# Mustaqil hisoblangan (hashlib/hmac bilan qo'lda) qiymat — kutubxona
# o'zgarib, imzo usuli jimgina boshqacha bo'lib qolsa test yiqiladi.
NAMUNA_IMZO = '07412767c8b6a5c694870d226a03595d33dfdab07ad262cd69ddf15fa7448e08'


class Hujjat(unittest.TestCase):
    def test_docs_yangilangan(self):
        try:
            sys.path.insert(0, str(ILDIZ / 'scripts'))
            import hujjat_yasash
        except ImportError as e:  # PyYAML o'rnatilmagan
            self.skipTest(f'PyYAML kerak: {e}')
        for yol, matn in hujjat_yasash.fayllar().items():
            with self.subTest(yol.name):
                self.assertTrue(yol.exists(), f'{yol.name} yo\'q — python scripts/hujjat_yasash.py')
                self.assertEqual(yol.read_text(encoding='utf-8'), matn,
                                 f'{yol.name} eskirgan — python scripts/hujjat_yasash.py')

    def test_readme_namuna_imzo(self):
        self.assertIn(NAMUNA_IMZO, (ILDIZ / 'README.md').read_text(encoding='utf-8'))

    def test_bundle_ichki_havolalar(self):
        try:
            sys.path.insert(0, str(ILDIZ / 'scripts'))
            import hujjat_yasash
        except ImportError as e:
            self.skipTest(f'PyYAML kerak: {e}')
        spec = hujjat_yasash.yig()
        komponentlar = spec['components']

        def aylan(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == '$ref':
                        self.assertTrue(v.startswith('#/components/'), v)
                        _, _, tur, nom = v.split('/')
                        self.assertIn(nom, komponentlar[tur], v)
                    else:
                        aylan(v)
            elif isinstance(obj, list):
                for v in obj:
                    aylan(v)
        aylan(spec)


if __name__ == '__main__':
    unittest.main()

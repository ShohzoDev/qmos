# QMOS — Qurilish Monitoringi Ochiq Standarti

**Versiya 1.0.** Qurilish obyektlari haqidagi jonli ma'lumotni pudratchi
tashkilotlar dasturidan markaziy monitoring tizimiga (qurilish inspeksiyasi,
hokimliklar) yuborish standarti.

```
Pudratchi dasturi (BuildOps yoki boshqa)  ──HTTPS + imzo──▶  Markaziy tizim
   o'z bazasi, o'z moliyasi                                 respublika → viloyat → tuman → obyekt
```

Standart bitta dasturga bog'lanmagan: istalgan ERP yoki hisob tizimi shu
hujjat bo'yicha ulana oladi. BuildOps — uning birinchi ilovasi.

## Tamoyillar

1. **Faqat yuborish.** Markaz tashkilot bazasiga hech qachon kirmaydi.
   Nima yuborilishini tashkilot nazorat qiladi.
2. **Ma'lumotni minimallashtirish.** Moliya, narx, ish haqi, qarzlar va
   ishchilarning shaxsiy ma'lumotlari **yuborilmaydi** — standartda ular
   uchun maydon yo'q va sxema ortiqcha maydonni rad etadi. Ishchilar faqat
   **soni** bilan beriladi. Yagona istisno — obyekt uchun mas'ul shaxsning
   ismi va telefoni (inspeksiya bog'lanishi uchun, ixtiyoriy).
3. **O'zgarmaslik.** Qabul qilingan hodisa o'zgartirilmaydi va
   o'chirilmaydi. Xato tuzatiladi — yangi hodisa bilan (`supersedes`).
   Kechagi kunni "jimgina to'g'rilab qo'yish" imkonsiz, har bir tuzatish
   tarixda ko'rinadi.
4. **Idempotentlik.** Har bir hodisaning noyob `event_id` si bor.
   Tarmoq uzilsa xuddi o'sha hodisani qayta yuborish xavfsiz — markaz
   `duplicate` deb javob beradi.
5. **Hudud — SOATO bo'yicha.** Viloyat va tuman kesimidagi ko'rinish
   obyekt manzilidagi SOATO kodlaridan avtomatik yig'iladi.

## Hodisa turlari

| `event_type` | Qachon yuboriladi | Asosiy maydonlar |
|---|---|---|
| `site.profile` | Obyekt yaratilganda va pasporti o'zgarganda (to'liq holat) | nomi, turi, SOATO manzil, koordinata, ruxsatnoma, buyurtmachi, muddatlar |
| `site.status` | Holat o'zgarganda | `planned` / `active` / `suspended` / `completed` / `cancelled`, sabab |
| `site.work_plan` | Smeta kiritilganda yoki o'zgarganda (to'liq ro'yxat) | ish turlari va **fizik** hajmlari (narxsiz) |
| `site.daily_report` | Har kuni (kun yakunida) | ishchilar soni (va tasdiqlanganlari), texnika, bajarilgan hajmlar, sifat |
| `site.photo` | Surat qo'shilganda | rasm (`POST /v1/media` orqali), vaqt, joylashuv |
| `site.incident` | Hodisa ro'y berganda | baxtsiz hodisa, xavfsizlik buzilishi, ish to'xtashi, material yetishmasligi |

Bajarilish foizi markazda hisoblanadi: `site.work_plan` dagi reja va
`site.daily_report` lardagi bajarilgan hajmlar nisbati.

`workforce.verified_present` — davomati joylashuv (geofence) yoki surat
bilan tasdiqlangan ishchilar soni. Qo'lda yozilgan son bilan farqi —
ma'lumot ishonchliligining ko'rsatkichi.

## Fayllar

| Yo'l | Nima |
|---|---|
| `openapi.yaml` | API: yo'llar, javoblar, autentifikatsiya (asosiy manba) |
| `qmos/schemas/v1/*.json` | Ma'lumot sxemalari, JSON Schema 2020-12 (asosiy manba) |
| `examples/v1/valid/` | To'g'ri misollar — har bir hodisa turi uchun |
| `examples/v1/invalid/` | Noto'g'ri misollar va kutilgan rad etish sababi (`_kutilgan.json`) |
| `qmos/` | Python kutubxonasi: tekshiruv va imzo (yuboruvchi ham, markaz ham ishlatadi) |
| `tests/` | Kontrakt testlari |
| `docs/` | Odam o'qiydigan hujjat — **sxemalardan yasaladi**, qo'lda tahrirlanmaydi |

Misollardagi tashkilot, obyekt, SOATO kodlari va shaxslar — shartli.

## Hujjatni ko'rish

`docs/index.html` faylini brauzerda oching (internet kerak — Redoc
kutubxonasi yuklanadi). `docs/openapi.json` — Postman, Swagger yoki kod
generatoriga beriladigan yagona fayl.

## Python'da foydalanish

```bash
pip install -e .
```

```python
import json
import qmos

hodisa = {...}  # site.daily_report va h.k.
xatolar = qmos.hodisa_xatolari(hodisa)
if xatolar:
    print(xatolar)  # [{'code': 'semantic', 'path': '/data/address/district_soato', 'message': '...'}]

tana = json.dumps({'events': [hodisa]}, ensure_ascii=False).encode('utf-8')
sarlavhalar = qmos.sign_request('KALIT_ID', 'MAXFIY_KALIT', 'POST', '/v1/events', tana)
# requests.post(MARKAZ + '/v1/events', data=tana, headers={**sarlavhalar, 'Content-Type': 'application/json'})
```

## Boshqa tillarda imzo (PHP, Java, C#, JS)

```
imzo_satri = timestamp + "\n" + "POST" + "\n" + "/v1/events" + "\n" + hex(sha256(tana))
X-QMOS-Signature = hex(hmac_sha256(secret, imzo_satri))
```

O'z ilovangizni shu namuna bilan tekshiring:

| | |
|---|---|
| secret | `maxfiy-kalit-32-bayt-uzunlikda!!` |
| timestamp | `1790000000` |
| method, path | `POST`, `/v1/events` |
| tana | `{"events":[]}` |
| natija | `07412767c8b6a5c694870d226a03595d33dfdab07ad262cd69ddf15fa7448e08` |

## Testlar

```bash
pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

Testlar quyidagilarni kafolatlaydi:

- har bir sxema to'g'ri va barcha havolalari ochiladi;
- barcha to'g'ri misollar o'tadi, noto'g'rilari **aynan kutilgan sabab
  bilan** rad etiladi;
- yangi hodisa turi misolsiz qo'shilsa — test yiqiladi;
- sxemalarda moliya yoki shaxsiy ma'lumot maydoni paydo bo'lsa — test
  yiqiladi;
- `docs/` sxemalardan farq qilsa — test yiqiladi.

Sxema yoki `openapi.yaml` o'zgargach:

```bash
python scripts/hujjat_yasash.py
```

## Versiyalash

- `1.x` — faqat **ixtiyoriy** maydon yoki yangi hodisa turi qo'shiladi.
  Eski yuboruvchilar hech narsa o'zgartirmasdan ishlashda davom etadi.
- `2.0` — majburiy maydon qo'shish, maydonni olib tashlash yoki ma'nosini
  o'zgartirish. Yangi `/v2/` yo'li bilan; `/v1/` kamida 12 oy parallel
  ishlaydi.

O'zgarishlar tarixi — `CHANGELOG.md`.

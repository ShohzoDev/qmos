"""openapi.yaml + qmos/schemas/v1/*.json -> docs/openapi.json va docs/index.html.

Sxemalar bitta faylga yig'iladi (bundle): har bir sxema fayli
`components/schemas` ichiga tushadi, fayllararo `$ref`lar ichki havolaga
aylanadi. Natija — tashqi faylga bog'liq bo'lmagan yagona spetsifikatsiya:
uni Swagger/Redoc/Postman yoki kod generatori to'g'ridan-to'g'ri o'qiydi.

    python scripts/hujjat_yasash.py           # fayllarni yangilaydi
    python scripts/hujjat_yasash.py --tekshir # eskirgan bo'lsa xato (CI uchun)

Hujjat sxemalardan YASALADI — qo'lda tahrirlanmaydi. Test
(tests/test_standart.py) docs/ papkasi sxemalarga mos ekanini tekshiradi.
"""
import copy
import json
import sys
from pathlib import Path

import yaml

ILDIZ = Path(__file__).resolve().parent.parent
SXEMA = ILDIZ / 'qmos' / 'schemas' / 'v1'
DOCS = ILDIZ / 'docs'
REDOC = 'https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js'


def nom(fayl):
    """'site-profile.json' -> 'SiteProfile'."""
    return ''.join(q.capitalize() for q in fayl.removesuffix('.json').split('-'))


def _ref_ozgart(ref, joriy):
    if ref.startswith('./qmos/schemas/v1/'):
        ref = ref.removeprefix('./qmos/schemas/v1/')
    if ref.startswith('#/components/'):
        return ref
    fayl, _, ichki = ref.partition('#')
    fayl = fayl or joriy
    if fayl is None:
        raise ValueError(f"Hal qilinmagan havola: {ref}")
    if not ichki:
        return f'#/components/schemas/{nom(fayl)}'
    if not ichki.startswith('/$defs/') or ichki.count('/') != 2:
        raise ValueError(f"Qo'llab-quvvatlanmaydigan havola: {ref}")
    return f'#/components/schemas/{nom(fayl)}_{ichki.split("/")[2]}'


def _aylan(obj, joriy):
    if isinstance(obj, dict):
        natija = {}
        for k, v in obj.items():
            if k == 'x-misol-fayli':
                # openapi.yaml'da misol qo'lda yozilmaydi — examples/ dagi
                # (testdan o'tgan) fayl joylanadi. Hujjatdagi misol doim to'g'ri.
                natija['example'] = json.loads((ILDIZ / v).read_text(encoding='utf-8'))
            else:
                natija[k] = _ref_ozgart(v, joriy) if k == '$ref' else _aylan(v, joriy)
        return natija
    if isinstance(obj, list):
        return [_aylan(v, joriy) for v in obj]
    return obj


def yig():
    spec = yaml.safe_load((ILDIZ / 'openapi.yaml').read_text(encoding='utf-8'))
    sxemalar = {}
    for f in sorted(SXEMA.glob('*.json')):
        s = json.loads(f.read_text(encoding='utf-8'))
        s.pop('$schema', None)
        defs = s.pop('$defs', {})
        for k, v in defs.items():
            sxemalar[f'{nom(f.name)}_{k}'] = _aylan(v, f.name)
        if set(s) - {'title', 'description'}:
            sxemalar[nom(f.name)] = _aylan(s, f.name)
    natija = _aylan(copy.deepcopy(spec), None)
    natija['components']['schemas'] = {**sxemalar, **natija['components'].get('schemas', {})}
    return natija


def html(spec):
    data = json.dumps(spec, ensure_ascii=False).replace('</', '<\\/')
    return f"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QMOS v{spec['info']['version']} — Qurilish Monitoringi Ochiq Standarti</title>
<style>body{{margin:0;padding:0}}</style>
</head>
<body>
<!-- Bu fayl scripts/hujjat_yasash.py tomonidan yasalgan. Qo'lda tahrirlamang. -->
<div id="redoc"></div>
<script src="{REDOC}"></script>
<script>
var spec = {data};
Redoc.init(spec, {{hideDownloadButton: false, expandResponses: "200,201", jsonSampleExpandLevel: 4}}, document.getElementById('redoc'));
</script>
</body>
</html>
"""


def fayllar():
    spec = yig()
    return {
        DOCS / 'openapi.json': json.dumps(spec, ensure_ascii=False, indent=2) + '\n',
        DOCS / 'index.html': html(spec),
    }


def main():
    tekshir = '--tekshir' in sys.argv
    eskirgan = []
    for yol, matn in fayllar().items():
        if tekshir:
            if not yol.exists() or yol.read_text(encoding='utf-8') != matn:
                eskirgan.append(yol.name)
        else:
            yol.parent.mkdir(exist_ok=True)
            yol.write_text(matn, encoding='utf-8', newline='\n')
            print('yozildi:', yol.relative_to(ILDIZ))
    if eskirgan:
        print('ESKIRGAN:', ', '.join(eskirgan), '— python scripts/hujjat_yasash.py ni ishga tushiring')
        sys.exit(1)


if __name__ == '__main__':
    main()

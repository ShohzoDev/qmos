"""So'rovlarni HMAC-SHA256 bilan imzolash va imzoni tekshirish.

    imzo_satri = timestamp + "\\n" + METHOD + "\\n" + path + "\\n" + hex(SHA256(tana))
    X-QMOS-Signature = hex(HMAC-SHA256(secret, imzo_satri))

Usul, yo'l va tana xeshi imzoga kiradi — imzolangan so'rovni boshqa
manzilga yoki o'zgartirilgan tana bilan qayta ishlatib bo'lmaydi. Vaqt
tamg'asi qayta yuborish (replay) hujumini 300 soniya bilan cheklaydi;
undan ichkaridagi takrorni markaz `event_id` idempotentligi bilan
zararsizlantiradi.
"""
import hashlib
import hmac
import time

VAQT_FARQI = 300  # soniya

SARLAVHA_KALIT = 'X-QMOS-Key-Id'
SARLAVHA_VAQT = 'X-QMOS-Timestamp'
SARLAVHA_IMZO = 'X-QMOS-Signature'


def _bayt(qiymat):
    return qiymat if isinstance(qiymat, bytes) else qiymat.encode('utf-8')


def imzo_satri(timestamp, method, path, tana):
    return '\n'.join([str(int(timestamp)), method.upper(), path, hashlib.sha256(_bayt(tana)).hexdigest()])


def imzola(secret, timestamp, method, path, tana):
    return hmac.new(_bayt(secret), imzo_satri(timestamp, method, path, tana).encode('utf-8'),
                    hashlib.sha256).hexdigest()


def sign_request(key_id, secret, method, path, tana, timestamp=None):
    """Yuboruvchi uchun: so'rovga qo'shiladigan sarlavhalar."""
    ts = int(time.time() if timestamp is None else timestamp)
    return {
        SARLAVHA_KALIT: key_id,
        SARLAVHA_VAQT: str(ts),
        SARLAVHA_IMZO: imzola(secret, ts, method, path, tana),
    }


def imzoni_tekshir(secret, timestamp, method, path, tana, imzo, hozir=None):
    """Markaz uchun: (to'g'rimi, sabab). Vaqt solishtirish doimiy vaqtda."""
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False, "X-QMOS-Timestamp noto'g'ri"
    hozir = time.time() if hozir is None else hozir
    if abs(hozir - ts) > VAQT_FARQI:
        return False, "vaqt farqi 300 soniyadan katta"
    kutilgan = imzola(secret, ts, method, path, tana)
    if not isinstance(imzo, str) or not hmac.compare_digest(kutilgan, imzo.lower()):
        return False, "imzo noto'g'ri"
    return True, ''

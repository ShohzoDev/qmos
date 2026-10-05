"""QMOS — Qurilish Monitoringi Ochiq Standarti, Python kutubxonasi.

    from qmos import hodisa_xatolari, sign_request, imzoni_tekshir

Yuboruvchi tizim (masalan BuildOps) hodisani yuborishdan OLDIN
`hodisa_xatolari()` bilan tekshiradi; markaz qabul qilganda ham AYNAN
shu funksiyani chaqiradi.
"""
from .imzo import imzoni_tekshir, imzola, sign_request
from .tekshiruv import hodisa_xatolari, mazmun_xatolari, sxema_xatolari, sxemalar, tekshir, validator

SPEC_VERSION = '1.0'

__all__ = [
    'SPEC_VERSION',
    'hodisa_xatolari', 'mazmun_xatolari', 'sxema_xatolari', 'sxemalar', 'tekshir', 'validator',
    'imzola', 'imzoni_tekshir', 'sign_request',
]

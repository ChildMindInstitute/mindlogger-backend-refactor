from fastapi import Depends

from apps.shared.locale import I18N
from infrastructure.http import get_language


def get_i18n(lang=Depends(get_language)) -> I18N:
    return I18N(lang)

from fastapi import Depends
from starlette.requests import Request

from apps.shared.locale import I18N
from infrastructure.http import get_language


def get_i18n(lang=Depends(get_language)) -> I18N:
    return I18N(lang)


def get_client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "")

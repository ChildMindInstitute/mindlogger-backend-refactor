from fastapi.middleware.cors import CORSMiddleware as _CORSMiddleware

from config import settings

__all__ = ["CORSMiddleware", "cors_options"]


class CORSMiddleware(_CORSMiddleware):
    pass


cors_options: dict = {
    "allow_origins": settings.cors.allow_origins,
    "allow_origin_regex": settings.cors.allow_origin_regex,
    "allow_credentials": settings.cors.allow_credentials,
    "allow_methods": settings.cors.allow_methods,
    "allow_headers": settings.cors.allow_headers,
    "expose_headers": settings.cors.expose_headers,
    "max_age": settings.cors.max_age,
}

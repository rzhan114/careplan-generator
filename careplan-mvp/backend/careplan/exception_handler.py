# careplan/exception_handler.py

from django.http import JsonResponse
from .exceptions import BaseAppException


def handle_exception(exc: Exception) -> JsonResponse:
    """
    统一把 exception 转成 JsonResponse。
    view 里 catch 到任何异常，都丢给这个函数处理。
    """
    if isinstance(exc, BaseAppException):
        return JsonResponse(exc.to_dict(), status=exc.http_status)

    # 未知错误，不暴露内部细节
    return JsonResponse(
        {
            "type": "error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "detail": {},
        },
        status=500,
    )
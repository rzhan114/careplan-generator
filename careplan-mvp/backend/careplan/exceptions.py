# careplan/exceptions.py

class BaseAppException(Exception):
    http_status = 500
    default_type = "error"
    default_code = "UNKNOWN_ERROR"
    default_message = "An unexpected error occurred"

    def __init__(self, message=None, code=None, detail=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.detail = detail or {}

    def to_dict(self):
        return {
            "type": self.default_type,
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


class ValidationError(BaseAppException):
    http_status = 400
    default_type = "validation"
    default_code = "VALIDATION_ERROR"
    default_message = "Input validation failed"


class BlockError(BaseAppException):
    http_status = 409
    default_type = "block"
    default_code = "BUSINESS_RULE_VIOLATION"
    default_message = "This action is not allowed"


class WarningException(BaseAppException):
    http_status = 200
    default_type = "warning"
    default_code = "WARNING"
    default_message = "Please review and confirm"
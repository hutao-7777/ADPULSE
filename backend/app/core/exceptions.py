"""Application-specific exceptions for AdPulse."""


class AdPulseException(Exception):
    """Base exception with a structured code/message pair.

    The ``code`` field is a business-level error code that can be exposed
    to API consumers, while ``status_code`` maps to the HTTP status.
    """

    def __init__(
        self,
        message: str,
        code: int = 500,
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AdPulseException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code=404, status_code=404)


class BadRequestException(AdPulseException):
    """Bad request."""

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message, code=400, status_code=400)

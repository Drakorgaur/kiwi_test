from src.exceptions import AppBadRequest


class CurrencyUnavailableException(LookupError, AppBadRequest):
    """Raised when currency rate is not available.

    This exception is handled as a bad request from the client.
    """
    pass

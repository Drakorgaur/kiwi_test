from src.exceptions import AppBadRequest


class CurrencyUnavailableException(LookupError, AppBadRequest):
    pass

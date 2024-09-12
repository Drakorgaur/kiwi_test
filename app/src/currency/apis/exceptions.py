from src.exceptions import AppServiceUnavailable


class ExternalAPIError(AppServiceUnavailable):
    """Raised when external API returns unexpected response, refused to connect or another error.

    This exception is handled as a service-unavailable error.
    See parent class for more info.
    """
    def __init__(self, message: str, api_cls: type):
        super().__init__(message)
        self.api_cls = api_cls

    def __str__(self):
        return f"<{self.api_cls.__name__}>: {super().__str__()}"

class AppBadRequest(Exception):
    """AppBadRequest exception.

    This exception should be a parent to any exception that means that request is not valid.

    See also: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
    """
    pass


class AppServiceUnavailable(Exception):
    """AppServiceUnavailable exception.

    This exception should be a parent to any exception that means that service is not available due to
    some external reasons.

    Example: external API is down.

    See also: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
    """
    pass

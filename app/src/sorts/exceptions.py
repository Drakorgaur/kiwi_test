from typing import Annotated

from src.exceptions import AppBadRequest


class SortingException(Exception):
    """Base class for exceptions in this module.

    Should not be raised directly.
    But it can be used to catch all exceptions in this module.
    """
    pass


class SortAlgorithmIsUnknown(SortingException, LookupError, AppBadRequest):
    """Raised when the sorting algorithm is unknown for the application."""
    def __init__(self, name: Annotated[str, "name of the sorting algorithm"]):
        super().__init__(f"Sorting algorithm `{name}` is unknown.")

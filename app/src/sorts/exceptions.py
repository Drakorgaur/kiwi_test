from typing import Annotated

from src.exceptions import AppBadRequest


class SortingException(Exception):
    """Base class for exceptions in this module."""
    pass


class SortAlgorithmIsUnknown(SortingException, LookupError, AppBadRequest):
    """Raised when the sorting algorithm is unknown."""
    def __init__(self, name: Annotated[str, "name of the sorting algorithm"]):
        super().__init__(f"Sorting algorithm `{name}` is unknown.")

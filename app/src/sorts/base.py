"""Module containing sorting algorithms for itineraries.


As this application is not connected to any API configuration service and can't configure available sorting algorithms,
it uses metaclass to register inherited classes of `AbstractSort`. This makes filters easy-to-register as code is
the source of truth.
"""
import contextvars
from abc import abstractmethod, ABC as Abstract
from decimal import Decimal
from typing import ClassVar, Iterable, Protocol, TypeVar, Type, TypeAlias, Final
from structlog import get_logger

from src.contracts.currency import Rates
from src.contracts.sort_itineraries import Itinerary
from src.currency.exceptions import CurrencyUnavailableException
from src.currency.fetch import fetch_currency
from src.sorts.exceptions import SortAlgorithmIsUnknown

logger = get_logger(__name__)

T = TypeVar('T')


class SupportsSort(Protocol[T]):
    """A protocol to support sorting of any iterable data.

    Class implementing this protocol should have a static method `sort`
        that accepts an iterable object and returns an iterable object of the same type.
    """

    @staticmethod
    def sort(data: Iterable[T]) -> Iterable[T]: ...


# Important info
# _itineraries_sorts is a dictionary that stores all registered sorting algorithms.
#   this dict should not be accessed directly, use `get_sort_algorithms` instead.
#   also it should be read-only.
#   TODO: frozen dict
#   _itineraries_sorts is updated by class `AbstractItinerariesSort` when a new class is created.
#   more info about PEP-0487: https://peps.python.org/pep-0487/
_itineraries_sorts: dict[str, Type["AnySort"]] = {}


def get_sort_algorithms() -> Iterable[str]:
    """Get all available sorting algorithms.

    See also: `_itineraries_sorts` notes

    Returns:
        dict_keys[str]: Dict-Key structure of algorithms.
    """
    return _itineraries_sorts.keys()


async def sort_itineraries(sort_name: str, data: Iterable[Itinerary]) -> Iterable[Itinerary]:
    """Sort itineraries by a given algorithm.

    Note: sort is sync. Currency rate fetch is async.

    Args:
        sort_name: name of the sorting algorithm.
        data: iterable of itineraries.

    Returns:
        Iterable[Itinerary]: (list of) sorted itineraries.

    Raises:
        SortAlgorithmIsUnknown: if the sorting algorithm is not available.
        ExternalAPIError: if currency rate fetch failed.
    """
    try:
        sort_cls: Type[AbstractItinerariesSort] = _itineraries_sorts[sort_name]
    except KeyError as exc:
        raise SortAlgorithmIsUnknown(sort_name) from exc

    return sort_cls(await fetch_currency()).sort(data)


class AbstractItinerariesSort(Abstract):
    """Abstract class for sorting algorithms.

    All sorting algorithms should inherit from this class.

    Important: this class registers all inherited classes in `_itineraries_sorts` dict.

    Attributes:
        name: name of the sorting algorithm.
            Important: this name is used to register the sorting algorithm.
            And bound string literal to the class.

    Protocols Implemented:
        SupportsSort: protocol to support sorting of any iterable data.

    Abstract Methods:
        sort: method to sort itineraries.
            This method should be implemented in a inherited class.
            It should return an iterable of sorted itineraries.
    """
    name: ClassVar[str]

    def __init__(self, currency_rates: Rates):
        self.currency_rates: Final[Rates] = currency_rates

    def __init_subclass__(cls: Type["AnySort"], **kwargs):
        """Register inherited classes in `_itineraries_sorts` dict.

        This method is called when a new class is created.
        It registers the class in `_itiner
        aries_sorts` dict.
        """
        super().__init_subclass__(**kwargs)
        try:
            _itineraries_sorts[cls.name] = cls
        except AttributeError:
            logger.warning(
                f"Sorting algorithm `{cls.__name__}` inherits from class::{AbstractItinerariesSort.__name__} "
                f"but does not have a `name` attribute set. This class is not registered as a sorting algorithm.",
                on="startup",
            )

    @abstractmethod
    def sort(self, itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]: ...


AnySort: TypeAlias = TypeVar("AnySort", bound=AbstractItinerariesSort)


# sorted is a powerful built-in function uses `PowerSort` (since 3.11, below 3.11 is used TimSort)
# under the hood, so it one of the fastest ways we can sort without using any accelerations like
# jit or numba, CAPI, etc.

class FastestItinerariesSort(AbstractItinerariesSort):
    """Fastest sort

    Sort itineraries by duration in minutes.

    See parent classes for more info.
    """
    name: ClassVar[str] = "fastest"

    def sort(self, itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        return sorted(itineraries, key=lambda itinerary: itinerary.duration_minutes)


class CheapestItinerariesSort(AbstractItinerariesSort):
    """Cheapest sort

    Sort itineraries by price in base currency.

    See parent classes for more info.
    """
    name: ClassVar[str] = "cheapest"

    def sort(self, itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        try:
            return sorted(
                itineraries,
                key=lambda itinerary: itinerary.price.amount / Decimal(self.currency_rates[itinerary.price.currency])
            )
        except KeyError as exc:
            raise CurrencyUnavailableException(f"Currency rate for {exc.args[0]} is not available") from exc


class BestItinerariesSort(AbstractItinerariesSort):
    """Best sort

    Sort itineraries by price * duration in minutes.

    See parent classes for more info.
    """
    name: ClassVar[str] = "best"

    def sort(self, itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        try:
            return sorted(
                itineraries,
                key=lambda itinerary: (
                        (
                                itinerary.price.amount
                                / Decimal(self.currency_rates[itinerary.price.currency])
                        )
                        * itinerary.duration_minutes
                )
            )
        except KeyError as exc:
            raise CurrencyUnavailableException(f"Currency rate for {exc.args[0]} is not available") from exc

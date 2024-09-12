"""Module containing sorting algorithms for itineraries.


As this application is not connected to any API configuration service and can't configure available sorting algorithms,
it uses metaclass to register inherited classes of `AbstractSort`. This makes filters easy-to-register as code is
the source of truth.
"""
import contextvars
from abc import ABCMeta, abstractmethod
from typing import ClassVar, Iterable, Callable, Protocol, TypeVar, Type
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
#   _itineraries_sorts is updated by meta-class `_AbstractSortMeta` when a new class is created.
#   more info about meta-classes: https://docs.python.org/3/reference/datamodel.html#metaclasses
_itineraries_sorts: dict[str, Type["AbstractItinerariesSort"]] = {}
# Important info 2
# _currency_ratio is a context variable that stores currency rates.
#   this variable should not be accessed directly, use `get_currency_ratio` instead.
#   ContextVar is used to separate currency rates for different OLTPs.
#   Also this is key-error handler and async-to-sync buffer.
#       As sorting algorithms are sync, but currency rate fetch is async.
#   More info about contextvars: https://docs.python.org/3/library/contextvars.html
_currency_ratio: contextvars.ContextVar[Rates] = contextvars.ContextVar("currency_ratio")


def get_currency_ratio(currency: str) -> float:
    """Get currency rate for given currency.

    Note: this uses `get` method of context variable, where is stored currency rates to base currency.
        For v1 sorting algorithm the base is USD.

    Args:
        currency: currency code in ISO 4217 standard.

    Returns:
        float: currency rate.

    Raises:
        CurrencyUnavailableException: if currency rate is not available.
    """
    try:
        return _currency_ratio.get()[currency]
    except LookupError as exc:
        raise CurrencyUnavailableException(f"Currency rate for {currency} is not available") from exc


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

    if sort_cls.needs_currency_rate:
        _currency_ratio.set(await fetch_currency())  # raises ExternalAPIError

    return sort_cls().sort(data)


class _AbstractSortMeta(ABCMeta):
    name: ClassVar[str]
    sort: Callable[[Iterable[Itinerary]], Iterable[Itinerary]]

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if object in cls.__bases__:
            # skip all abstract classes
            return cls

        try:
            _itineraries_sorts[cls.name] = cls  # noqa
        except AttributeError:
            logger.warning(
                f"Sorting algorithm `{name}` inherits from class::AbstractSort "
                f"but does not have a `name` attribute set. This class is not registered as a sorting algorithm.",
                on="startup",
            )

        return cls


class AbstractItinerariesSort(metaclass=_AbstractSortMeta):
    """Abstract class for sorting algorithms.

    All sorting algorithms should inherit from this class.

    Important: this is a abstract class that has a meta class `_AbstractSortMeta`
        that registers all inherited classes except abstract ones.
        Abstract classes are the classes that bases *directly* from meta-class (via __bases__ attribute).

    Attributes:
        name: name of the sorting algorithm.
            Important: this name is used to register the sorting algorithm.
            And bound string literal to the class.
        needs_currency_rate: flag to indicate if the sorting algorithm needs currency rate.
            If True, the currency rate is fetched before sorting itineraries.
            (fetch may also be cached, see module `currency.fetch`)

    Protocols Implemented:
        SupportsSort: protocol to support sorting of any iterable data.

    Abstract Methods:
        sort: method to sort itineraries.
            This method should be implemented in a inherited class.
            It should return an iterable of sorted itineraries.
    """
    name: ClassVar[str]
    needs_currency_rate: ClassVar[bool] = False

    @staticmethod
    @abstractmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]: ...


# sorted is a powerful built-in function uses `PowerSort` (since 3.11, below 3.11 is used TimSort)
# under the hood, so it one of the fastest ways we can sort without using any accelerations like
# jit or numba, CAPI, etc.

class FastestItinerariesSort(AbstractItinerariesSort):
    """Fastest sort

    Sort itineraries by duration in minutes.

    See parent classes for more info.
    """
    name: ClassVar[str] = "fastest"

    @staticmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        return sorted(itineraries, key=lambda itinerary: itinerary.duration_minutes)


class CheapestItinerariesSort(AbstractItinerariesSort):
    """Cheapest sort

    Sort itineraries by price in base currency.

    See parent classes for more info.
    """
    name: ClassVar[str] = "cheapest"
    needs_currency_rate: ClassVar[bool] = True

    @staticmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        return sorted(
            itineraries,
            key=lambda itinerary: itinerary.price.amount / get_currency_ratio(itinerary.price.currency)
        )


class BestItinerariesSort(AbstractItinerariesSort):
    """Best sort

    Sort itineraries by price * duration in minutes.

    See parent classes for more info.
    """
    name: ClassVar[str] = "best"
    needs_currency_rate: ClassVar[bool] = True

    @staticmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        return sorted(
            itineraries,
            key=lambda itinerary: (
                    (
                            itinerary.price.amount
                            / get_currency_ratio(itinerary.price.currency)
                    )
                    * itinerary.duration_minutes
            )
        )

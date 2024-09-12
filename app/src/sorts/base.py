"""


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
    @staticmethod
    def sort(data: Iterable[T]) -> Iterable[T]: ...


_itineraries_sorts: dict[str, Type["AbstractSort"]] = {}
_currency_ratio: contextvars.ContextVar[Rates] = contextvars.ContextVar("currency_ratio")


def get_currency_ratio(currency: str) -> float:
    try:
        return _currency_ratio.get()[currency]
    except LookupError as exc:
        raise CurrencyUnavailableException(f"Currency rate for {currency} is not available") from exc


def get_sort_algorithms() -> Iterable[str]:
    return _itineraries_sorts.keys()


async def sort_itineraries(sort_name: str, data: Iterable[Itinerary]) -> Iterable[Itinerary]:
    try:
        sort: Type[AbstractSort] = _itineraries_sorts[sort_name]
    except KeyError as exc:
        raise SortAlgorithmIsUnknown(sort_name) from exc

    if sort.needs_currency_rate:
        _currency_ratio.set(await fetch_currency())

    return sort().sort(data)


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


class AbstractSort(metaclass=_AbstractSortMeta):
    needs_currency_rate: ClassVar[bool] = False

    @staticmethod
    @abstractmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]: ...


# sorted is a powerful built-in function uses `PowerSort` (since 3.11, below 3.11 is used TimSort)
# under the hood, so it one of the fastest ways we can sort without using any accelerations like
# jit or numba, CAPI, etc.

class FastestSort(AbstractSort):
    name: ClassVar[str] = "fastest"

    @staticmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        return sorted(itineraries, key=lambda itinerary: itinerary.duration_minutes)


class CheapestSort(AbstractSort):
    name: ClassVar[str] = "cheapest"
    needs_currency_rate: ClassVar[bool] = True

    @staticmethod
    def sort(itineraries: Iterable[Itinerary]) -> Iterable[Itinerary]:
        return sorted(
            itineraries,
            key=lambda itinerary: itinerary.price.amount / get_currency_ratio(itinerary.price.currency)
        )


class BestSort(AbstractSort):
    """
    best: Design an algorithm to find the optimal balance between price and duration.
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
                            / _currency_ratio.get()[itinerary.price.currency]
                    )
                    * itinerary.duration_minutes
            )
        )

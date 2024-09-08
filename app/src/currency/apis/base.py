from abc import ABC as Abstract, abstractmethod
from collections.abc import Callable
from typing import TypeVar, Awaitable, Final

from src.contracts.currency import Rates
from src.currency.apis.exceptions import ExternalAPIError


BASE_CURRENCY: Final[str] = "USD"  # TODO: from config


def classmethod_interpret_api_error(*exceptions) -> Callable:
    """
    TODO: doc that
    :param exceptions:
    :return:
    """
    # TODO: here we can use ParamSpec from typing module
    def wrapper(func: Callable[[str | None], Awaitable[Rates]]) -> Callable[[str], Awaitable[Rates]]:
        async def inner(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except exceptions as exc:
                raise ExternalAPIError("Api returned unexpected response.", args[0]) from exc

        return inner

    return wrapper


class CurrencyRateProvider(Abstract):
    def __hash__(self):
        """ for lru_cache """
        return hash(self.url)

    @property
    @abstractmethod
    def url(self) -> str: ...

    @abstractmethod
    def get_rates(self, base) -> Rates: ...

    @classmethod
    def construct(cls) -> "CurrencyRateProvider":
        """
        Use this to construct from a config / env.
        If other api requires keys, etc.
        :return:
        """
        return cls()


AnyCurrencyApi = TypeVar("AnyCurrencyApi", bound=CurrencyRateProvider)

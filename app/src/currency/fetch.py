import contextlib
import datetime

from typing import Type, ClassVar, Final

import environ

from diskcache import Cache, Timeout as CacheTimeout, Lock

from src.contracts.currency import Rates
from src.currency.apis.base import AnyCurrencyApi, BASE_CURRENCY
from src.currency.apis.exchangerate import ExchangeRate
from src.currency.config import CurrencyCacheConfig

__all__ = ["fetch_currency"]


class _LocalStorage:
    """Local storage for currency rates.
    Uses getter-setter interface.

    Attributes:
        _cache: dict[str, dict[str, Any]]:
            key: base currency code
            value: dict with keys:
                - rates: currency rates relative to the base currency.
                - expires: timestamp when rates expire.
        config: CurrencyCacheConfig: configuration for currency rates.
            See config class for more info.
    """
    config: ClassVar[CurrencyCacheConfig] = environ.to_config(CurrencyCacheConfig)

    def __init__(self):
        self._cache: Final[Cache] = Cache(self.config.cache_path.as_posix())

    def get(self, base: str) -> Rates | None:
        """Get currency rates from the cache.

        Args:
            base: currency code in ISO 4217 standard.

        Returns:
            Rates | None: currency rates relative to the base currency.
                None if rates are not available or expired.
        """
        with contextlib.suppress(CacheTimeout):
            return self._cache.get(base, retry=True)

    def set(self, data: Rates, *, base: str):
        """Set currency rates to the cache.

        Cache ttl is set to the end of the day.

        Args:
            data: currency rates relative to the base currency.
            base: currency code in ISO 4217 standard.
        """
        expiration_date: Final[datetime.date] = datetime.datetime.now().date() + datetime.timedelta(days=1)

        self._cache.set(key=base, value=data, expire=int(expiration_date.strftime("%s")))

    def lock(self, base: str) -> Lock:
        """Get lock for the given base currency.

        Args:
            base: currency code in ISO 4217 standard.

        Returns:
            Lock: lock for the given base currency.
        """
        return Lock(self._cache, base)

# (private for this module) Singleton instance of the local storage.
# Holds currency rates in RAM in runtime.
_local_storage: Final[_LocalStorage] = _LocalStorage()


async def _fetch_currency_online(api_cls: Type[AnyCurrencyApi], base: str) -> Rates:
    """Fetch currency rates for given base currency.

    Args:
        api_cls: class-object (not instance) of the API to use for fetching currency rates.
            Api class should be a correct subclass of `CurrencyRateProvider`.
        base: currency code in ISO 4217 standard.
            All returned rates are relative to this currency.

    Returns:
        Rates: currency rates relative to the base currency.

    Raises:
        ExternalAPIError: if currency rate fetch failed.
    """
    api: AnyCurrencyApi = api_cls()
    return await api.get_rates(base=base)  # raises ExternalAPIError


async def _fetch_currency_online_and_store(
        base: str = BASE_CURRENCY,
        api_cls: Type[AnyCurrencyApi] = ExchangeRate
) -> Rates:
    """Fetch currency rates for given base currency.
     Store them in the local storage after the fetch.

    Args:
        base: currency code in ISO 4217 standard.
            All returned rates are relative to this currency.
        api_cls: class-object (not instance) of the API to use for fetching currency rates.
            Api class should be a correct subclass of `CurrencyRateProvider`.

    Returns:
        Rates: currency rates relative to the base currency.

    Raises:
        ExternalAPIError: if currency rate fetch failed.
    """
    rates: Rates = await _fetch_currency_online(
        api_cls=api_cls,
        base=base
    )

    _local_storage.set(rates, base=base)

    return rates


async def fetch_currency(*, base: str = BASE_CURRENCY, api_cls: Type[AnyCurrencyApi] = ExchangeRate) -> Rates:
    """ Fetch currency rates for given base currency.

    Note: before fetching rates, it checks if rates are available and is valid (not expired) in cache storage.

    Args:
        base: currency code in ISO 4217 standard.
            All returned rates are relative to this currency.
        api_cls: class-object (not instance) of the API to use for fetching currency rates.
            Api class should be a correct subclass of `CurrencyRateProvider`.

    Returns:
        Rates: currency rates relative to the base currency.

    Raises:
        ExternalAPIError: if currency rate fetch failed.
    """

    with _local_storage.lock(base):
        return (
                _local_storage.get(base)  # returns None on cache miss
                or await _fetch_currency_online_and_store(base=base, api_cls=api_cls)  # raises ExternalAPIError
        )

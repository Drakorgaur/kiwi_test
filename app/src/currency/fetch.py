import time

from typing import Type, ClassVar, TypedDict, Final

import environ

from src.contracts.currency import Rates
from src.currency.apis.base import AnyCurrencyApi, BASE_CURRENCY
from src.currency.apis.exchangerate import ExchangeRate

__all__ = ["fetch_currency"]

from src.currency.config import CurrencyConfig


class _LocalStorage:
    """Local storage for currency rates.
    Uses getter-setter interface.

    This class is used to store currency rates in RAM.

    Danger: this class is not thread-safe.
    TODO: make it thread-safe.

    Important: for this class to work correctly, it should be used as a singleton.

    Attributes:
        _cache: dict[str, dict[str, Any]]:
            key: base currency code
            value: dict with keys:
                - rates: currency rates relative to the base currency.
                - expires: timestamp when rates expire.
        config: CurrencyConfig: configuration for currency rates.
            see config class for more info.

    Classes:
        InternalSchema: TypedDict - is used for typing purposes.
            Shows how data is stored in the cache.
    """
    config: ClassVar[CurrencyConfig] = environ.to_config(CurrencyConfig)

    class InternalSchema(TypedDict):
        rates: Rates
        expires: float

    def __init__(self):
        self._cache: dict[str, _LocalStorage.InternalSchema] = {}

    def get(self, base: str) -> Rates | None:
        """Get currency rates from the cache.

        Args:
            base: currency code in ISO 4217 standard.

        Returns:
            Rates | None: currency rates relative to the base currency.
                None if rates are not available or expired.
        """
        base_rates: _LocalStorage.InternalSchema = self._cache.get(base, {})
        if base_rates.get("expires", 0) < time.time():
            return
        return base_rates["rates"]

    def set(self, data: Rates, *, base: str):
        """Set currency rates to the cache.

        Args:
            data: currency rates relative to the base currency.
            base: currency code in ISO 4217 standard.
        """
        self._cache[base] = {
            "rates": data,
            "expires": time.time() + self.config.cache_ttl
        }


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
    return (
            _local_storage.get(base)  # returns None on cache miss
            or await _fetch_currency_online_and_store(base=base, api_cls=api_cls)  # raises ExternalAPIError
    )

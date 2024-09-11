import datetime
import time

from typing import Type, ClassVar, TypedDict

import environ

from src.contracts.currency import Rates
from src.currency.apis.base import AnyCurrencyApi, BASE_CURRENCY
from src.currency.apis.exchangerate import ExchangeRate

__all__ = ["fetch_currency"]

from src.currency.config import CurrencyConfig


class _LocalStorage:
    config: ClassVar[CurrencyConfig] = environ.to_config(CurrencyConfig)

    class InternalSchema(TypedDict):
        rates: Rates
        expires: float

    def __init__(self):
        self._cache: dict[str, _LocalStorage.InternalSchema] = {}

    def get(self, base: str) -> Rates | None:
        base_rates = self._cache.get(base, {})
        if base_rates.get("expires", 0) < time.time():
            return
        return base_rates["rates"]

    def set(self, data: Rates, *, base: str):
        self._cache[base] = {
            "rates": data,
            "expires": time.time() + self.config.cache_ttl
        }


_local_storage = _LocalStorage()


async def _fetch_currency_online(_: str, api_cls: Type[AnyCurrencyApi], base: str) -> Rates:
    """ Datetime is a caching key.
    :param _:
    :param api_cls:
    :return:
    """
    api: AnyCurrencyApi = api_cls.construct()
    return await api.get_rates(base=base)


async def _fetch_currency_online_and_store(
        base: str = BASE_CURRENCY,
        api_cls: Type[AnyCurrencyApi] = ExchangeRate
) -> Rates:
    rates: Rates = await _fetch_currency_online(
        datetime.date.today().isoformat(),
        api_cls=api_cls,
        base=base
    )

    _local_storage.set(rates, base=base)

    return rates


async def fetch_currency(*, base: str = BASE_CURRENCY, api_cls: Type[AnyCurrencyApi] = ExchangeRate) -> Rates:
    return (
            _local_storage.get(base)
            or await _fetch_currency_online_and_store(base=base, api_cls=api_cls)
    )

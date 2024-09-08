import contextlib
import datetime
import json
import time

from functools import lru_cache
from abc import ABC as Abstract
from json import JSONDecodeError
from pathlib import Path
from typing import Type, ClassVar, TypedDict

import aiofiles
import environ

from src.contracts.currency import Rates
from src.currency.apis.base import AnyCurrencyApi, BASE_CURRENCY
from src.currency.apis.exchangerate import ExchangeRate

__all__ = ["fetch_currency"]

from src.currency.config import CurrencyConfig


class _LocalStorage(Abstract):
    config: ClassVar[CurrencyConfig] = environ.to_config(CurrencyConfig)

    class InternalSchema(TypedDict):
        rates: Rates
        expires: float

    @classmethod
    def base_file(cls, base: str) -> Path:
        return cls.config.local_dir / f"{base}.json"

    # TODO: cache somehow, file reading is slow
    @classmethod
    async def get(cls, base: str) -> Rates:
        # TODO: should be lock on fs level
        # still may throw PermissionDenied, etc.
        with contextlib.suppress(FileNotFoundError, JSONDecodeError):
            async with aiofiles.open(cls.base_file(base), "rb") as f:
                data: cls.InternalSchema = json.loads(await f.read())  # throws JSONDecodeError
                if data["expires"] > time.time():
                    return data["rates"]

    @classmethod
    async def set(cls, data: Rates, *, base: str):
        with contextlib.suppress(FileNotFoundError):
            async with aiofiles.open(cls.base_file(base), "w") as f:
                data: cls.InternalSchema = {
                    "rates": data,
                    "expires": time.time() + cls.config.cache_ttl
                }
                await f.write(json.dumps(data))


@lru_cache(maxsize=2)
def _fetch_currency_online(_: datetime, api_cls: Type[AnyCurrencyApi], base: str) -> Rates:
    """ Datetime is a caching key.
    :param _:
    :param api_cls:
    :return:
    """
    # TODO:

    return {
        "USD": 1.0,
        "EUR": 0.8,
        "GBP": 0.7,
        "JPY": 120.0,
    }
    # api: AnyCurrencyApi = api_cls.construct()
    # return api.get_rates(base=base)


async def _fetch_currency_online_and_store(
        base: str = BASE_CURRENCY,
        api_cls: Type[AnyCurrencyApi] = ExchangeRate
) -> Rates:
    rates: Rates = _fetch_currency_online(
        datetime.date.today(),
        api_cls=api_cls,
        base=base
    )

    await _LocalStorage.set(rates, base=base)

    return rates


async def fetch_currency(*, base: str = BASE_CURRENCY, api_cls: Type[AnyCurrencyApi] = ExchangeRate) -> Rates:
    return (
        await _LocalStorage.get(base)
        or await _fetch_currency_online_and_store(base=base, api_cls=api_cls)
    )

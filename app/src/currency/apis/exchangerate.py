"""
documentation https://www.exchangerate-api.com/docs/free
terms_of_use https://www.exchangerate-api.com/
"""
from json import JSONDecodeError
from typing import ClassVar

import httpx

from src.contracts.currency import Rates
from src.currency.apis.base import CurrencyRateProvider, classmethod_interpret_api_error


class ExchangeRate(CurrencyRateProvider):
    url: ClassVar[str] = "https://open.er-api.com/v6/latest"

    @classmethod
    @classmethod_interpret_api_error(httpx.HTTPStatusError, JSONDecodeError, KeyError)
    async def get_rates(cls, base: str) -> Rates:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{cls.url}/{base}")  # TODO: handle
            response.raise_for_status()      # raises HTTPStatusError
            return response.json()["rates"]  # raises JSONDecodeError, KeyError

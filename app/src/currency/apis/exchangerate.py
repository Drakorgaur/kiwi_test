from json import JSONDecodeError
from typing import ClassVar

import environ
import httpx

from src.contracts.currency import Rates
from src.currency.apis.base import CurrencyRateProvider, classmethod_interpret_api_error


class ExchangeRate(CurrencyRateProvider):
    """ExchangeRate API provider.

    documentation https://www.exchangerate-api.com/docs/free
    terms_of_use https://www.exchangerate-api.com/

    Attributes:
        url: str: url for the API.
            built directly from the environment variable on stage of class creation.

    Classes:
        Config - configuration from environment variables.
    """
    @environ.config(prefix="EXCHANGE_RATE_API")
    class Config:
        url: str = environ.var()

    url: ClassVar[str] = environ.to_config(Config).url

    @classmethod
    @classmethod_interpret_api_error(httpx.HTTPStatusError, JSONDecodeError, KeyError)
    async def get_rates(cls, base: str) -> Rates:
        """Get currency rates for given base currency.

        Args:
            base: currency code in ISO 4217 standard.
                All returned rates are relative to this currency.

        Returns:
            Rates: currency rates relative to the base currency.

        Raises:
            ExternalAPIError: if API returned unexpected
                see `classmethod_interpret_api_error` for more info.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{cls.url}/{base}")  # TODO: handle
            response.raise_for_status()      # raises HTTPStatusError
            return response.json()["rates"]  # raises JSONDecodeError, KeyError

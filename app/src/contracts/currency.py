from typing import TypeAlias

from pydantic import BaseModel


Rates: TypeAlias = dict[str, float]


class CurrencyApiResponse(BaseModel):
    # for open.er-api.com/v6/latest
    result: str
    provider: str
    documentation: str
    terms_of_use: str
    time_last_update_unix: int
    time_last_update_utc: str
    time_next_update_unix: int
    time_next_update_utc: str
    time_eol_unix: int
    base_code: str
    rates: Rates

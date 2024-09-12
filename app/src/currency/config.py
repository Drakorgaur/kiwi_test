import environ


@environ.config(prefix="CURRENCY")
class CurrencyConfig:
    """Class holding config for currency rates.

    Attributes:
        cache_ttl: int: time in seconds for the currency rates to be cached.
            Default is 1 day.
    """
    cache_ttl: int = environ.var(converter=int, default=60 * 60 * 24)  # 1 day

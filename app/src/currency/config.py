import environ


@environ.config(prefix="CURRENCY")
class CurrencyConfig:
    cache_ttl: int = environ.var(converter=int, default=60 * 60 * 24)  # 1 day

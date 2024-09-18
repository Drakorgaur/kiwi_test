from pathlib import Path

import environ


@environ.config(prefix="CURRENCY")
class CurrencyCacheConfig:
    """Class holding config for currency rates.

    Attributes:
        cache_path: Path: path to the cache directory.
    """
    cache_path: Path = environ.var(converter=Path, default="/mnt/cache")

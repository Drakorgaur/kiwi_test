from pathlib import Path

import environ


@environ.config(prefix="CURRENCY")
class CurrencyConfig:
    local_dir: Path = environ.var(converter=Path, default=Path("/tmp/cache"))
    cache_ttl: int = environ.var(converter=int, default=60 * 60 * 24)  # 1 day

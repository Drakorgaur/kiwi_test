import time
from typing import ClassVar
from unittest import TestCase


from src.currency.fetch import _LocalStorage  # noqa


class TestLocalCaching(TestCase):
    BASE: ClassVar[str] = "USD"

    def test_local_set_get(self):
        storage = _LocalStorage()
        data = {self.BASE: 1, "EUR": 0.8}
        storage.set(data, base=self.BASE)
        a = storage.get(self.BASE)
        self.assertEqual(a, data)

    def test_no_return_on_expired_cache(self):
        data = {self.BASE: 1, "EUR": 0.8}
        storage = _LocalStorage()
        storage.set(data, base=self.BASE)
        patched_data: storage.InternalSchema = storage._cache[self.BASE]
        patched_data["expires"] = 0

        a = storage.get("USD")
        self.assertIsNone(a)

    def test_cache_time(self):
        storage = _LocalStorage()
        storage.config.cache_ttl = 100
        data = {self.BASE: 1, "EUR": 0.8}
        storage.set(data, base=self.BASE)

        self.assertAlmostEqual(storage._cache[self.BASE]["expires"], time.time() + 100, delta=5)

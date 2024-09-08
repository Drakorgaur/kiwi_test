import json
import time
from unittest import mock, IsolatedAsyncioTestCase

import aiofiles

from src.currency.fetch import _LocalStorage  # noqa


class TestLocalCaching(IsolatedAsyncioTestCase):
    @staticmethod
    def make_fs():
        content = []
        mock_fs = mock.MagicMock(
            write=content.append,
            read=lambda *args, **kwargs: content.pop(0)
        )
        return content, mock_fs

    @classmethod
    def setUpClass(cls):
        # https://github.com/Tinche/aiofiles?tab=readme-ov-file#writing-tests-for-aiofiles
        aiofiles.threadpool.wrap.register(mock.MagicMock)(  # noqa
            lambda *args, **kwargs: aiofiles.threadpool.AsyncBufferedIOBase(*args, **kwargs)  # noqa
        )

    async def test_local_set_get(self):
        content, mock_fs = self.make_fs()

        with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_fs):
            data = {"USD": 1, "EUR": 0.8}
            await _LocalStorage.set(data, base="USD")
            a = await _LocalStorage.get("USD")
            self.assertEqual(a, data)

    async def test_no_return_on_expired_cache(self):
        content, mock_fs = self.make_fs()

        with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_fs):
            data = {"USD": 1, "EUR": 0.8}
            await _LocalStorage.set(data, base="USD")
            patched_data: _LocalStorage.InternalSchema = json.loads(content[0])
            patched_data["expires"] = 0
            content[0] = json.dumps(patched_data)

            a = await _LocalStorage.get("USD")
            self.assertIsNone(a)

    async def test_cache_time(self):
        content, mock_fs = self.make_fs()

        with mock.patch('aiofiles.threadpool.sync_open', return_value=mock_fs):
            _LocalStorage.config.cache_ttl = 100
            data = {"USD": 1, "EUR": 0.8}
            await _LocalStorage.set(data, base="USD")

            cache: _LocalStorage.InternalSchema = json.loads(content[0])
            self.assertAlmostEqual(cache["expires"], time.time() + 100, delta=5)


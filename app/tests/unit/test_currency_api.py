import unittest
from unittest import mock, IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from httpx import HTTPStatusError

from src.currency.apis.base import classmethod_interpret_api_error
from src.currency.apis.exceptions import ExternalAPIError
with mock.patch("environ.to_config") as mock_to_config:
    from src.currency.apis.exchangerate import ExchangeRate
    ExchangeRate.url = "https://test.com"


class TestCurrencyApi(IsolatedAsyncioTestCase):
    async def test_decorator_works_properly(self):
        CustExc = type("CustExc", (Exception,), {})
        CustCls = type("CustCls", (), {})

        async def classmethod_throw_exception(_=CustCls):
            # oh no, api errored with CustExc
            raise CustExc("Test")

        async def classmethod_throw_unhandled_exception(_=CustCls):
            # no error
            raise KeyError("Test")

        with self.assertRaises(ExternalAPIError):
            await (classmethod_interpret_api_error(
                CustExc  # catch this exc
            )(
                classmethod_throw_exception  # on this function
            ))(CustCls)  # call

        with self.assertRaises(KeyError):
            await (classmethod_interpret_api_error(
                CustExc  # catch this exc
            )(
                classmethod_throw_unhandled_exception  # on this function
            ))(CustCls)

    @staticmethod
    def patch_get(mock_client_ctx):
        get_mock = mock.AsyncMock(name="get_mock")  # 52
        response_mock = mock.AsyncMock(name="response_mock")  # 92
        sentinel = object()
        response_mock.json = MagicMock(name="json")
        response_mock.json.return_value = {"rates": sentinel}
        response_mock.raise_for_status = MagicMock(name="raise_for_status")
        get_mock.return_value = response_mock
        client = MagicMock()
        client.get = get_mock
        mock_client_ctx.return_value = client
        return get_mock, sentinel

    async def test_exchange_rate_api(self):
        with mock.patch("httpx.AsyncClient.__aenter__") as mock_client_ctx:
            get_mock, sentinel = self.patch_get(mock_client_ctx)

            response = await ExchangeRate.get_rates("USD")

            get_mock.assert_awaited_with(ExchangeRate.url + "/USD")
            self.assertEqual(response, sentinel)

    async def test_exchange_rate_api_fails(self):
        with (mock.patch("httpx.AsyncClient.__aenter__") as mock_client_ctx):
            get_mock, _ = self.patch_get(mock_client_ctx)
            response_mock = get_mock.return_value
            raise_for_status_mock = MagicMock()
            response_mock.raise_for_status = raise_for_status_mock  # change from Async to Sync mock
            raise_for_status_mock.side_effect = HTTPStatusError("Test", response=None, request=None)  # noqa

            with self.assertRaises(ExternalAPIError):
                await ExchangeRate.get_rates("USD")

    async def test_exchange_rate_api_fails_2(self):
        with mock.patch("httpx.AsyncClient.__aenter__") as mock_client_ctx:
            get_mock, _ = self.patch_get(mock_client_ctx)
            response_mock = get_mock.return_value
            response_mock.raise_for_status.side_effect = ValueError("Test")

            with self.assertRaises(ValueError):
                await ExchangeRate.get_rates("USD")


if __name__ == '__main__':
    unittest.main()

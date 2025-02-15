import asyncio
from unittest import TestCase
from unittest.mock import MagicMock

from typing_extensions import Awaitable

from hummingbot.connector.exchange.nobitex.nobitex_auth import NobitexAuth
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest


class NobitexAuthTests(TestCase):

    def setUp(self) -> None:
        self._api_key = "testApiKey"

    # TODO: First check done
    def async_run_with_timeout(self, coroutine: Awaitable, timeout: float = 1):
        ret = asyncio.get_event_loop().run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    # TODO: First check done
    def test_rest_authenticate(self):
        now = 1234567890.000
        mock_time_provider = MagicMock()
        mock_time_provider.time.return_value = now

        params = {
            "symbol": "LTCBTC",
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": 1,
            "price": "0.1",
        }

        auth = NobitexAuth(api_key=self._api_key, time_provider=mock_time_provider)
        request = RESTRequest(method=RESTMethod.GET, params=params, is_auth_required=True)
        configured_request = self.async_run_with_timeout(auth.rest_authenticate(request))

        self.assertEqual({"Authorization": f"Token {self._api_key}"}, configured_request.headers)

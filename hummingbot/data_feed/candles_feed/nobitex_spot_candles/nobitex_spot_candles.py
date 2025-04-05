import asyncio
import logging
from decimal import Decimal
from typing import List, Optional

from hummingbot.core.network_iterator import NetworkStatus
from hummingbot.core.web_assistant.connections.data_types import WSJSONRequest
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.data_feed.candles_feed.candles_base import CandlesBase
from hummingbot.data_feed.candles_feed.nobitex_spot_candles import constants as CONSTANTS
from hummingbot.logger import HummingbotLogger


class NobitexSpotCandles(CandlesBase):

    def __init__(self, trading_pair: str, interval: str = "1m", max_records: int = 150):
        self._ws_id = 1
        super().__init__(trading_pair, interval, max_records)

    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    @property
    def name(self):
        return f"nobitex_{self._trading_pair}"

    @property
    def rest_url(self):
        return CONSTANTS.REST_URL

    @property
    def wss_url(self):
        return CONSTANTS.WSS_URL

    @property
    def health_check_url(self):
        # return self.rest_url + CONSTANTS.HEALTH_CHECK_ENDPOINT
        return None

    @property
    def candles_url(self):
        return self.rest_url + CONSTANTS.CANDLES_ENDPOINT

    @property
    def candles_endpoint(self):
        return CONSTANTS.CANDLES_ENDPOINT

    @property
    def candles_max_result_per_rest_request(self):
        return CONSTANTS.MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    @property
    def rate_limits(self):
        return CONSTANTS.RATE_LIMITS

    @property
    def intervals(self):
        return CONSTANTS.INTERVALS

    async def check_network(self) -> NetworkStatus:
        # rest_assistant = await self._api_factory.get_rest_assistant()
        # await rest_assistant.execute_request(url=self.health_check_url,
        #                                      throttler_limit_id=CONSTANTS.HEALTH_CHECK_ENDPOINT)
        return NetworkStatus.CONNECTED

    def get_exchange_trading_pair(self, trading_pair):
        return trading_pair.replace("-", "").upper()

    def _get_rest_candles_params(self,
                                 start_time: Optional[int] = None,
                                 end_time: Optional[int] = None,
                                 limit: Optional[int] = CONSTANTS.MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST) -> dict:
        params = {
            "symbol": self._ex_trading_pair,
            "resolution": CONSTANTS.INTERVALS[self.interval],
            # "interval": self.interval,
            "countback": limit
        }
        if end_time:
            params["to"] = end_time
        return params

    def _parse_rest_candles(self, data: dict, end_time: Optional[int] = None) -> List[List[float]]:
        candles = []

        if data["s"] == "ok":
            for i in range(len(data["t"])):

                candles.append([
                    self.ensure_timestamp_in_seconds(data["t"][i]),
                    # open price
                    data["o"][i],
                    # high price
                    data["h"][i],
                    # low price
                    data["l"][i],
                    # close price
                    data["c"][i],
                    # volume
                    data["v"][i],
                    # quote asset volume
                    (Decimal(data["l"][i]) + Decimal(data["c"][i])) * Decimal(data["v"][i]) / 2,
                    # number of trades
                    0.,
                    # taker buy base volume
                    0.,
                    # taker buy quote volume
                    0.
                ])

        else:
            raise Exception(f"Error fetching candles: {data['e']}")

        return candles

    async def _connected_websocket_assistant(self) -> WSAssistant:
        ws: WSAssistant = await self._api_factory.get_ws_assistant()
        await ws.connect(ws_url=self.wss_url, ping_timeout=self._ping_timeout)

        # send connect request after connecting to the websocket based on Nobitex documentation
        payload = {"connect": {}, "id": 1}
        connect_request: WSJSONRequest = WSJSONRequest(payload=payload)
        await ws.send(connect_request)

        # reset the ws_id to 2 because the first id is used for the connect request
        self._ws_id = 2
        return ws

    def ws_subscription_payload(self):
        # candle_params = [f"{self._ex_trading_pair.lower()}@kline_{self.interval}"]
        # payload = {
        #     "method": "SUBSCRIBE",
        #     "params": candle_params,
        #     "id": 1
        # }
        payload = {"subscribe": {"channel": f"public:candle-{self._ex_trading_pair.upper()}-{CONSTANTS.INTERVALS[self.interval]}"}, "id": self._ws_id}
        self._ws_id += 1
        return payload

    async def _subscribe_channels(self, ws: WSAssistant):
        """
        Subscribes to the candles events through the provided websocket connection.
        :param ws: the websocket assistant used to connect to the exchange
        """
        try:
            subscribe_candles_request: WSJSONRequest = WSJSONRequest(payload=self.ws_subscription_payload())
            await ws.send(subscribe_candles_request)
            self.logger().info("Subscribed to public klines...")
        except asyncio.CancelledError:
            raise
        except Exception:
            self.logger().error(
                "Unexpected error occurred subscribing to public klines...",
                exc_info=True
            )
            raise

    def _parse_websocket_message(self, data: dict):
        # Nobitex websocket message example:
        # {
        #     "push": {
        #         "channel": "public:candle-USDTIRT-60",
        #         "pub": {
        #             "data": {
        #                 "t": 1743777000,
        #                 "o": 104777.0,
        #                 "h": 104777.0,
        #                 "l": 104700.0,
        #                 "c": 104700.0,
        #                 "v": 11100.69437859
        #             },
        #             "offset": 756922
        #         }
        #     }
        # }

        if data == {}:
            # Nobitex sends an empty message when the connection is established
            pong_response = WSJSONRequest(payload={})
            # Send a pong response to keep the connection alive
            return pong_response

        candles_row_dict = {}
        c = data and data.get("push", {}).get("pub", {}).get("data", None)
        if c:
            candles_row_dict["timestamp"] = self.ensure_timestamp_in_seconds(c["t"])
            candles_row_dict["open"] = c["o"]
            candles_row_dict["high"] = c["h"]
            candles_row_dict["low"] = c["l"]
            candles_row_dict["close"] = c["c"]
            candles_row_dict["volume"] = c["v"]
            candles_row_dict["quote_asset_volume"] = (Decimal(c["l"]) + Decimal(c["c"])) * Decimal(c["v"]) / 2
            candles_row_dict["n_trades"] = 0.
            candles_row_dict["taker_buy_base_volume"] = 0.
            candles_row_dict["taker_buy_quote_volume"] = 0.
            return candles_row_dict

from bidict import bidict

# from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
from hummingbot.core.api_throttler.data_types import RateLimit

# REST_URL = "https://api.nobitex.ir"
REST_URL = "https://testnetapi.nobitex.ir"
# HEALTH_CHECK_ENDPOINT = "/api/v3/ping"
CANDLES_ENDPOINT = "/market/udf/history"

# WSS_URL = "wss://wss.nobitex.ir/connection/websocket"
WSS_URL = "wss://testwss.nobitex.ir/connection/websocket"

INTERVALS = bidict({
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "3h": "180",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "2d": "2D",
    "3d": "3D"
})
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 500
# REQUEST_WEIGHT = "REQUEST_WEIGHT"

RATE_LIMITS = [
    # RateLimit(REQUEST_WEIGHT, limit=6000, time_interval=60),
    RateLimit(CANDLES_ENDPOINT, limit=1200, time_interval=60)
]

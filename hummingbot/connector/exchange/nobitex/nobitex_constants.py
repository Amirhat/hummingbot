import sys

from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.common import OrderType
from hummingbot.core.data_type.in_flight_order import OrderState

CLIENT_ID_PREFIX = "N-"
MAX_ORDER_ID_LEN = 32
# SECONDS_TO_WAIT_TO_RECEIVE_MESSAGE = 30 * 0.8

WS_HEARTBEAT_TIME_INTERVAL = 25  # other exchanges are 20 - 30 seconds, nobitex is 25 seconds

DEFAULT_DOMAIN = "nobitex_main"  # main domain is "nobitex_main" and test domain is "nobitex_testnet"


PRIVATE_TRADE_CHANNEL = "trade_channel"
PRIVATE_ORDER_CHANNEL = "order_channel"
PRIVATE_WALLET_CHANNEL = "wallet_channel"

EVENT_TYPE_ORDER_CHANGE = "order_change"

# URLs

REST_URLS = {
    # "nobitex_main": "https://api.nobitex.ir",
    "nobitex_main": "https://testnetapi.nobitex.ir",
    # "nobitex_testnet": "https://testnetapi.nobitex.ir"
}

WSS_URL = {
    # "nobitex_main": "wss://wss.nobitex.ir/connection/websocket",
    "nobitex_main": "wss://testwss.nobitex.ir/connection/websocket",
    # "nobitex_testnet": "wss://testwss.nobitex.ir/connection/websocket"
}

WSS_PUBLIC_URL = {
    "nobitex_main": WSS_URL["nobitex_main"],
    # "nobitex_testnet": WSS_URL["nobitex_testnet"]
}

WSS_PRIVATE_URL = {
    "nobitex_main": WSS_URL["nobitex_main"],
    # "nobitex_testnet": WSS_URL["nobitex_testnet"]
}


SIDE_BUY = "buy"
SIDE_SELL = "sell"


NOBITEX_ORDER_BOOK_PATH = "/v3/orderbook/"  # GET /v3/orderbook/:SYMBOL
SNAPSHOT_PATH_URL = NOBITEX_ORDER_BOOK_PATH

NOBITEX_ALL_ORDER_BOOK_PATHS = "/v3/orderbook/all"  # GET /v3/orderbook/all to get all order book

NOBITEX_ALL_PRICE_PATH = "/market/stats"  # GET /market/stats to get all price
NOBITEX_GLOBAL_PRICE_PATH = "/market/global-stats"  # GET /market/global-stats to get all global price

NOBITEX_SERVER_OPTIONS_PATH = "/v2/options"  # GET /v2/options to get server options and status

NOBITEX_TRADE_PATH = "/v2/trades/"  # GET /v2/trades/:SYMBOL to get trades
TRADE_PATH_URL = NOBITEX_TRADE_PATH


NOBITEX_PLACE_ORDER_PATH = "/market/orders/add"  # POST /market/orders/add to create a new order
ORDER_PATH_URL = NOBITEX_PLACE_ORDER_PATH
# NOBITEX_ORDER_DETAILS_PATH
NOBITEX_ORDER_STATUS_PATH = "/market/orders/status"  # POST /market/orders/status to get user order status
ORDER_STATUS_PATH_URL = NOBITEX_ORDER_STATUS_PATH

NOBITEX_UPDATE_ORDER_STATUS_PATH = (
    "/market/orders/update-status"  # POST /market/orders/update-status to cancel an order
)
UPDATE_ORDER_STATUS_PATH = NOBITEX_UPDATE_ORDER_STATUS_PATH

NOBITEX_ORDER_LIST_PATH = "/market/orders/list"  # GET /market/orders/list to get user orders
PRIVATE_ORDERS_PATH = NOBITEX_ORDER_LIST_PATH

NOBITEX_USER_TRADES_PATH = "/market/trades/list"  # GET /market/trades/list to get user trades
MY_TRADES_PATH_URL = NOBITEX_USER_TRADES_PATH

NOBITEX_WALLET_BALANCE_PATH = "/users/wallets/balance"  # POST /users/wallets/balance to get single wallet balance
NOBITEX_PROFILE_PATH = "/users/profile"  # GET /users/profile to get user profile
NOBITEX_WALLET_LIST_PATH = "/users/wallets/list"  # GET /users/wallets/list to get user wallets
USER_WALLETS_PATH = NOBITEX_WALLET_LIST_PATH

NOBITEX_WALLET_TRANSACTIONS_PATH = (
    "/users/wallets/transactions/list"  # GET /users/wallets/transactions/list to get transactions history
)


NOBITEX_WS_ORDERS_CHANNEL = "public:orderbook-"  # public:orderbook-BTCIRR
NOBITEX_WS_OHLC_CHANNEL = (
    "public:candle-"  # public:candle-{marketSymbol}-{resolution} like public:candle-BTCIRR-60 that means 60 min candle
)


UNKNOWN_ORDER_MESSAGE = "No Order matches the given query."
UNKNOWN_ORDER_ERROR_CODE = 404

NOBITEX_WS_CHANNELS = {NOBITEX_WS_ORDERS_CHANNEL, NOBITEX_WS_OHLC_CHANNEL}


WS_CONNECTION_LIMIT_ID = "WSConnection"
WS_REQUEST_LIMIT_ID = "WSRequest"
WS_SUBSCRIPTION_LIMIT_ID = "WSSubscription"
WS_LOGIN_LIMIT_ID = "WSLogin"


ORDER_STATE = {
    "Open": OrderState.OPEN,
    "NEW": OrderState.OPEN,
    "Active": OrderState.OPEN,  # if partial: true => OrderState.PARTIALLY_FILLED
    "Canceled": OrderState.CANCELED,
    "Done": OrderState.FILLED,
    "Inactive": OrderState.CREATED,
}

ORDER_TYPE_MAP = {
    OrderType.LIMIT: "limit",
    OrderType.MARKET: "market",
    # OrderType.LIMIT_MAKER: "post_only",
}

NO_LIMIT = sys.maxsize


RATE_LIMITS = [
    # Public Market Data APIs
    RateLimit(limit_id=NOBITEX_ALL_PRICE_PATH, limit=20, time_interval=60),  # GET /market/stats
    RateLimit(limit_id=NOBITEX_GLOBAL_PRICE_PATH, limit=100, time_interval=600),  # POST /market/global-stats
    # Public Market Data APIs - 300 requests per minute
    RateLimit(limit_id=NOBITEX_ORDER_BOOK_PATH, limit=300, time_interval=60),  # /v3/orderbook
    RateLimit(limit_id=NOBITEX_TRADE_PATH, limit=60, time_interval=60),  # /v2/trades
    RateLimit(limit_id="public_stats", limit=20, time_interval=60),  # /market/stats
    RateLimit(limit_id=NOBITEX_SERVER_OPTIONS_PATH, limit=300, time_interval=60),  # /v2/options
    # OHLC Data APIs - 30 requests per minute
    RateLimit(limit_id="ohlc_data", limit=300, time_interval=60),  # /market/udf/history
    # Authentication - 30 requests per 10 minutes
    RateLimit(limit_id="auth_login", limit=30, time_interval=600),  # /auth/login/
    RateLimit(limit_id="auth_logout", limit=30, time_interval=600),  # /auth/logout/
    # Trading APIs - 60 requests per minute
    RateLimit(limit_id=NOBITEX_PLACE_ORDER_PATH, limit=300, time_interval=600),  # /market/orders/add
    RateLimit(limit_id=NOBITEX_ORDER_STATUS_PATH, limit=300, time_interval=60),  # /market/orders/status
    RateLimit(limit_id=NOBITEX_ORDER_LIST_PATH, limit=30, time_interval=60),  # /market/orders/list
    RateLimit(limit_id=NOBITEX_UPDATE_ORDER_STATUS_PATH, limit=90, time_interval=60),  # /market/orders/update-status
    RateLimit(limit_id=MY_TRADES_PATH_URL, limit=30, time_interval=60),  # /market/trades/list
    # Account/Wallet APIs - 30 requests per minute
    RateLimit(limit_id=NOBITEX_WALLET_LIST_PATH, limit=20, time_interval=120),  # /users/wallets/list
    RateLimit(limit_id="wallet_balance", limit=60, time_interval=120),  # /users/wallets/balance
    RateLimit(limit_id="user_profile", limit=30, time_interval=60),  # /users/profile
    RateLimit(limit_id="wallet_transactions", limit=60, time_interval=120),  # /users/wallets/transactions/list
]

import asyncio
import time
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from bidict import bidict

from hummingbot.connector.constants import s_decimal_NaN
from hummingbot.connector.exchange.nobitex import nobitex_constants as CONSTANTS, nobitex_web_utils as web_utils
from hummingbot.connector.exchange.nobitex.nobitex_api_order_book_data_source import NobitexAPIOrderBookDataSource
from hummingbot.connector.exchange.nobitex.nobitex_api_user_stream_data_source import NobitexAPIUserStreamDataSource
from hummingbot.connector.exchange.nobitex.nobitex_auth import NobitexAuth
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair, split_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderState, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import DeductedFromReturnsTradeFee, TokenAmount, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

if TYPE_CHECKING:
    from hummingbot.client.config.config_helpers import ClientConfigAdapter


class NobitexExchange(ExchangePyBase):
    UPDATE_ORDER_STATUS_MIN_INTERVAL = 10.0

    web_utils = web_utils

    real_time_balance_update = False

    # TODO: check if this is correct
    def __init__(
        self,
        client_config_map: "ClientConfigAdapter",
        nobitex_api_key: str,
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
        domain: str = CONSTANTS.DEFAULT_DOMAIN,
    ):
        self.api_key = nobitex_api_key
        self._domain = domain
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs
        self._last_trades_poll_nobitex_timestamp = 1.0
        self._naming_dictionary = None
        super().__init__(client_config_map)

    # TODO: check if this is correct
    @staticmethod
    def nobitex_order_type(order_type: OrderType) -> str:
        # if order_type is OrderType.LIMIT_MAKER:
        #     return "limit_maker"
        if order_type is OrderType.LIMIT:
            return "limit"
        elif order_type is OrderType.MARKET:
            return "market"
        else:
            raise ValueError(f"Invalid order type: {order_type}")

    @staticmethod
    def nobitex_convert_received_rls_to_irt(trading_pair: str, value: Decimal) -> Decimal:
        _, quote = split_hb_trading_pair(trading_pair=trading_pair)
        if quote == "IRT":
            return value / 10
        else:
            return value

    # TODO: check if this is correct
    @staticmethod
    def to_hb_order_type(nobitex_type: str) -> OrderType:
        return OrderType[nobitex_type]

    # TODO: First check done
    @property
    def authenticator(self):
        return NobitexAuth(api_key=self.api_key, time_provider=self._time_synchronizer)

    # TODO: First check done
    @property
    def name(self) -> str:
        return "nobitex"

    # TODO: First check done
    @property
    def rate_limits_rules(self):
        return CONSTANTS.RATE_LIMITS

    # TODO: First check done
    @property
    def domain(self):
        return self._domain

    # TODO: First check done
    @property
    def client_order_id_max_length(self):
        return CONSTANTS.MAX_ORDER_ID_LEN

    # TODO: First check done
    @property
    def client_order_id_prefix(self):
        return CONSTANTS.CLIENT_ID_PREFIX

    # TODO: First check done, this is not match to the binance
    @property
    def trading_rules_request_path(self):
        return CONSTANTS.NOBITEX_SERVER_OPTIONS_PATH

    # TODO: First check done, this is not match to the binance
    @property
    def trading_pairs_request_path(self):
        return CONSTANTS.NOBITEX_SERVER_OPTIONS_PATH

    # TODO: First check done, this is not match to the binance
    @property
    def check_network_request_path(self):
        return CONSTANTS.NOBITEX_SERVER_OPTIONS_PATH

    # TODO: First check done
    @property
    def trading_pairs(self):
        return self._trading_pairs

    # TODO: First check done
    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return True

    # TODO: First check done
    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    # TODO: First check done
    def supported_order_types(self):
        return [OrderType.LIMIT, OrderType.MARKET]

    # TODO: First check done
    async def get_all_pairs_prices(self) -> List[Dict[str, str]]:
        pairs_prices = await self._api_get(
            path_url=CONSTANTS.NOBITEX_ALL_ORDER_BOOK_PATHS, limit_id=CONSTANTS.SNAPSHOT_PATH_URL
        )
        return pairs_prices

    # TODO: First check done, this is not match to the binance
    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        # error_description = str(request_exception)
        # is_time_synchronizer_related = ("-1021" in error_description
        #                                 and "Timestamp for this request" in error_description)
        # return is_time_synchronizer_related
        return False

    # TODO: First check done
    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        return str(CONSTANTS.UNKNOWN_ORDER_ERROR_CODE) in str(
            status_update_exception
        ) and CONSTANTS.UNKNOWN_ORDER_MESSAGE in str(status_update_exception)

    # TODO: First check done
    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        return str(CONSTANTS.UNKNOWN_ORDER_ERROR_CODE) in str(
            cancelation_exception
        ) and CONSTANTS.UNKNOWN_ORDER_MESSAGE in str(cancelation_exception)

    # TODO: First check done
    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(throttler=self._throttler, _domain=self._domain, auth=self._auth)

    # TODO: First check done
    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return NobitexAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            connector=self,
            domain=self.domain,
            api_factory=self._web_assistants_factory,
        )

    # TODO: First check done
    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return NobitexAPIUserStreamDataSource(
            auth=self._auth,
            trading_pairs=self._trading_pairs,
            connector=self,
            api_factory=self._web_assistants_factory,
            domain=self.domain,
        )

    # TODO: First check done
    # TODO: change the fee schema to calculate fee based on base currency
    # in nobitex, the fee is calculated also based on the base currency
    def _get_fee(
        self,
        base_currency: str,
        quote_currency: str,
        order_type: OrderType,
        order_side: TradeType,
        amount: Decimal,
        price: Decimal = s_decimal_NaN,
        is_maker: Optional[bool] = None,
    ) -> TradeFeeBase:
        is_maker = order_type is OrderType.LIMIT_MAKER

        return DeductedFromReturnsTradeFee(percent=self.estimate_fee_pct(is_maker))

    def translate_currency(self, currency: str) -> str:
        if currency.upper().endswith("USDT"):
            return "usdt"
        elif currency.upper().endswith("IRT"):
            return "rls"
        else:
            raise ValueError(f"Invalid currency: {currency}")

    # TODO: First check done
    async def _place_order(
        self,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        trade_type: TradeType,
        order_type: OrderType,
        price: Decimal,
        **kwargs,
    ) -> Tuple[str, float]:
        order_result = None
        amount_str = f"{amount:f}"

        type_str = NobitexExchange.nobitex_order_type(order_type)
        side_str = CONSTANTS.SIDE_BUY if trade_type is TradeType.BUY else CONSTANTS.SIDE_SELL
        # symbol = await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)

        base, quote = split_hb_trading_pair(trading_pair=trading_pair)

        currency = str(quote).lower()

        api_params = {
            "type": side_str,  # buy or sell
            "execution": type_str,  # limit or market
            "srcCurrency": base.lower(),  # base currency in lower case btc_irr
            "amount": amount_str,
            "clientOrderId": order_id,
        }

        if order_type is OrderType.LIMIT or order_type is OrderType.LIMIT_MAKER:
            if currency == "usdt":
                api_params["dstCurrency"] = "usdt"
                p = price
            elif currency == "irt":
                # convert IRT to RLS
                api_params["dstCurrency"] = "rls"
                p = price * 10
            else:
                raise ValueError(f"Invalid quote currency: {currency}")

            price_str = f"{p:f}"
            api_params["price"] = price_str

        try:
            order_result = await self._api_post(
                path_url=CONSTANTS.ORDER_PATH_URL, data=api_params, is_auth_required=True
            )
            o_id = str(order_result["order"]["id"])
            transact_time = datetime.fromisoformat(order_result["order"]["created_at"]).timestamp()
        except IOError as e:
            error_description = str(e)
            is_server_overloaded = (
                "status is 503" in error_description
                and "Unknown error, please check your request or try again later." in error_description
            )
            if is_server_overloaded:
                o_id = "UNKNOWN"
                transact_time = self._time_synchronizer.time()
            else:
                raise
        return o_id, transact_time

    # TODO: First check done
    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        # symbol = await self.exchange_symbol_associated_to_pair(trading_pair=tracked_order.trading_pair)
        api_params = {
            "order": int(tracked_order.exchange_order_id),
            "clientOrderId": tracked_order.client_order_id,  # order_id,
            "status": "canceled",
        }
        cancel_result = await self._api_post(
            path_url=CONSTANTS.UPDATE_ORDER_STATUS_PATH, data=api_params, is_auth_required=True
        )
        if cancel_result.get("status") == "ok" and cancel_result.get("updatedStatus") == "Canceled":
            return True
        return False

    # TODO: First check done
    async def _format_trading_rules(self, exchange_info_dict: Dict[str, Any]) -> List[TradingRule]:

        nobitex_info = exchange_info_dict.get("nobitex", {})

        amountPrecisions = nobitex_info.get("amountPrecisions", {})
        pricePrecisions = nobitex_info.get("pricePrecisions", {})
        minNotional = nobitex_info.get("minOrders", {})

        retval = []
        for pair in amountPrecisions.keys():
            try:

                amount_precision = amountPrecisions.get(pair)
                price_precision = pricePrecisions.get(pair)

                if pair.upper().endswith("USDT"):
                    quote = "USDT"
                    notional_case = "usdt"
                elif pair.upper().endswith("IRT"):
                    # Decides based on test
                    price_precision = Decimal(price_precision) / 10
                    quote = "IRT"
                    notional_case = "rls"
                else:
                    self.logger().warning(f"Error parsing the trading pair rule {pair}. Skipping.")
                    continue

                base = pair.replace(quote, "").upper()
                trading_pair = combine_to_hb_trading_pair(base=base, quote=quote)

                min_notional = minNotional.get(notional_case)

                if min_notional is None or amount_precision is None or price_precision is None:
                    self.logger().warning(f"Error parsing the trading pair rule {pair}. Skipping.")
                    continue

                min_order_size = Decimal(amount_precision)
                min_price_increment = Decimal(price_precision)
                min_base_amount_increment = Decimal(amount_precision)
                min_notional_size = Decimal(min_notional)

                retval.append(
                    TradingRule(
                        trading_pair,
                        min_order_size=min_order_size,
                        min_price_increment=min_price_increment,
                        min_base_amount_increment=min_base_amount_increment,
                        min_notional_size=min_notional_size,
                    )
                )

            except Exception:
                self.logger().exception(f"Error parsing the trading pair rule {pair}. Skipping.")
        return retval

    # TODO: First check done
    # async def _status_polling_loop_fetch_updates(self):
    #     await self._update_order_fills_from_trades()
    #     await super()._status_polling_loop_fetch_updates()

    # TODO: check later, update fees information from the exchange
    async def _update_trading_fees(self):
        """
        Update fees information from the exchange
        """
        pass

    # TODO: check later, Important to update the balance in real time
    async def _user_stream_event_listener(self):
        """
        This functions runs in background continuously processing the events received from the exchange by the user
        stream data source. It keeps reading events from the queue until the task is interrupted.
        The events received are balance updates, order updates and trade events.
        """
        async for event_message in self._iter_user_event_queue():
            try:
                event_type = event_message.get("event_type")

                if event_type == CONSTANTS.EVENT_TYPE_ORDER_CHANGE:
                    order = event_message
                    trades = order.get("trades", [])
                    client_order_id = order.get("client_order_id")
                    exchange_order_id = order.get("exchange_order_id")
                    trading_pair = order.get("trading_pair")
                    tracked_order = self._order_tracker.all_fillable_orders.get(client_order_id)

                    if tracked_order is not None:
                        for trade in trades:
                            trade_id = trade.get("id")

                            fee = TradeFeeBase.new_spot_fee(
                                fee_schema=self.trade_fee_schema(),
                                trade_type=tracked_order.trade_type,
                                percent_token=trade.get("commission_asset"),
                                flat_fees=[
                                    TokenAmount(amount=trade.get("commission"), token=trade.get("commission_asset"))
                                ],
                            )
                            trade_update = TradeUpdate(
                                trade_id=trade_id,
                                client_order_id=client_order_id,
                                exchange_order_id=exchange_order_id,
                                trading_pair=trading_pair,
                                fee=fee,
                                fill_base_amount=Decimal(trade.get("amount")),
                                fill_quote_amount=Decimal(trade.get("total")),
                                fill_price=Decimal(trade.get("price")),
                                fill_timestamp=trade.get("timestamp") * 1e-3,
                            )
                            self._order_tracker.process_trade_update(trade_update)
                        update_timestamp = max(
                            max(trade.get("timestamp") for trade in trades) if trades else 0, order.get("created_at")
                        )
                        order_update = OrderUpdate(
                            trading_pair=trading_pair,
                            update_timestamp=update_timestamp * 1e-3,
                            new_state=order.get("order_status"),
                            client_order_id=client_order_id,
                            exchange_order_id=exchange_order_id,
                        )
                        self._order_tracker.process_order_update(order_update=order_update)

                # elif event_type == "outboundAccountPosition":
                #     balances = event_message["B"]
                #     for balance_entry in balances:
                #         asset_name = balance_entry["a"]
                #         free_balance = Decimal(balance_entry["f"])
                #         total_balance = Decimal(balance_entry["f"]) + Decimal(balance_entry["l"])
                #         self._account_available_balances[asset_name] = free_balance
                #         self._account_balances[asset_name] = total_balance

            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error in user stream listener loop.", exc_info=True)
                await self._sleep(5.0)

    # TODO: check later, Important to update the order fills in real time
    # async def _update_order_fills_from_trades(self):
    # """
    # This is intended to be a backup measure to get filled events with trade ID for orders,
    # in case Nobitex's user stream events are not working.
    # NOTE: It is not required to copy this functionality in other connectors.
    # This is separated from _update_order_status which only updates the order status without producing filled
    # events, since Nobitex's get order endpoint does not return trade IDs.
    # The minimum poll interval for order status is 10 seconds.
    # """
    # small_interval_last_tick = self._last_poll_timestamp / self.UPDATE_ORDER_STATUS_MIN_INTERVAL
    # small_interval_current_tick = self.current_timestamp / self.UPDATE_ORDER_STATUS_MIN_INTERVAL
    # long_interval_last_tick = self._last_poll_timestamp / self.LONG_POLL_INTERVAL
    # long_interval_current_tick = self.current_timestamp / self.LONG_POLL_INTERVAL

    # if (long_interval_current_tick > long_interval_last_tick
    #         or (self.in_flight_orders and small_interval_current_tick > small_interval_last_tick)):
    #     query_time = int(self._last_trades_poll_nobitex_timestamp * 1e3)
    #     self._last_trades_poll_nobitex_timestamp = self._time_synchronizer.time()
    #     order_by_exchange_id_map = {}
    #     for order in self._order_tracker.all_fillable_orders.values():
    #         order_by_exchange_id_map[order.exchange_order_id] = order

    #     tasks = []
    #     trading_pairs = self.trading_pairs
    #     for trading_pair in trading_pairs:
    #         params = {
    #             "symbol": await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)
    #         }
    #         if self._last_poll_timestamp > 0:
    #             params["startTime"] = query_time
    #         tasks.append(self._api_get(
    #             path_url=CONSTANTS.MY_TRADES_PATH_URL,
    #             params=params,
    #             is_auth_required=True))

    #     self.logger().debug(f"Polling for order fills of {len(tasks)} trading pairs.")
    #     results = await safe_gather(*tasks, return_exceptions=True)

    #     for trades, trading_pair in zip(results, trading_pairs):

    #         if isinstance(trades, Exception):
    #             self.logger().network(
    #                 f"Error fetching trades update for the order {trading_pair}: {trades}.",
    #                 app_warning_msg=f"Failed to fetch trade update for {trading_pair}."
    #             )
    #             continue
    #         for trade in trades:
    #             exchange_order_id = str(trade["orderId"])
    #             if exchange_order_id in order_by_exchange_id_map:
    #                 # This is a fill for a tracked order
    #                 tracked_order = order_by_exchange_id_map[exchange_order_id]
    #                 fee = TradeFeeBase.new_spot_fee(
    #                     fee_schema=self.trade_fee_schema(),
    #                     trade_type=tracked_order.trade_type,
    #                     percent_token=trade["commissionAsset"],
    #                     flat_fees=[TokenAmount(amount=Decimal(trade["commission"]), token=trade["commissionAsset"])]
    #                 )
    #                 trade_update = TradeUpdate(
    #                     trade_id=str(trade["id"]),
    #                     client_order_id=tracked_order.client_order_id,
    #                     exchange_order_id=exchange_order_id,
    #                     trading_pair=trading_pair,
    #                     fee=fee,
    #                     fill_base_amount=Decimal(trade["qty"]),
    #                     fill_quote_amount=Decimal(trade["quoteQty"]),
    #                     fill_price=Decimal(trade["price"]),
    #                     fill_timestamp=trade["time"] * 1e-3,
    #                 )
    #                 self._order_tracker.process_trade_update(trade_update)
    #             elif self.is_confirmed_new_order_filled_event(str(trade["id"]), exchange_order_id, trading_pair):
    #                 # This is a fill of an order registered in the DB but not tracked any more
    #                 self._current_trade_fills.add(TradeFillOrderDetails(
    #                     market=self.display_name,
    #                     exchange_trade_id=str(trade["id"]),
    #                     symbol=trading_pair))
    #                 self.trigger_event(
    #                     MarketEvent.OrderFilled,
    #                     OrderFilledEvent(
    #                         timestamp=float(trade["time"]) * 1e-3,
    #                         order_id=self._exchange_order_ids.get(str(trade["orderId"]), None),
    #                         trading_pair=trading_pair,
    #                         trade_type=TradeType.BUY if trade["isBuyer"] else TradeType.SELL,
    #                         order_type=OrderType.LIMIT_MAKER if trade["isMaker"] else OrderType.LIMIT,
    #                         price=Decimal(trade["price"]),
    #                         amount=Decimal(trade["qty"]),
    #                         trade_fee=DeductedFromReturnsTradeFee(
    #                             flat_fees=[
    #                                 TokenAmount(
    #                                     trade["commissionAsset"],
    #                                     Decimal(trade["commission"])
    #                                 )
    #                             ]
    #                         ),
    #                         exchange_trade_id=str(trade["id"])
    #                     ))
    #                 self.logger().info(f"Recreating missing trade in TradeFill: {trade}")

    # TODO: First check done
    async def _update_orders_fills(self, orders: List[InFlightOrder]):
        """
        This function overrides the default implementation in the base class
        because Nobitex's get trades endpoint returns data page by page

        This method in the base ExchangePyBase, makes an API call for each order.
        Given the rate limit of the API method and the breadth of info provided by the method
        the mitigation proposal is to collect all orders in one shot, then parse them
        Note that this is limited to 100 orders, but we got orders page by page
        """
        if len(orders) == 0:
            return

        # fist get data page by page
        page = 0
        all_fills_response = []
        while page >= 0:
            params = {"pageSize": 100}

            if page > 0:
                params["page"] = page

            fills_response = await self._api_get(
                path_url=CONSTANTS.MY_TRADES_PATH_URL, params=params, is_auth_required=True
            )

            hasnext = fills_response.get("hasNext")
            page = (page + 1) if hasnext else -1
            all_fills_response.extend(fills_response.get("trades", []))

        for order in orders:
            try:
                trade_updates = await self._nobitex_all_trades_updates_for_order(
                    order=order, all_orders_fills_response=all_fills_response
                )
                for trade_update in trade_updates:
                    self._order_tracker.process_trade_update(trade_update)
            except asyncio.CancelledError:
                raise
            except Exception as request_error:
                self.logger().warning(
                    f"Failed to fetch trade updates for order {order.client_order_id}. Error: {request_error}",
                    exc_info=request_error,
                )

    # TODO: First check done
    async def _nobitex_all_trades_updates_for_order(
        self, order: InFlightOrder, all_orders_fills_response: list
    ) -> List[TradeUpdate]:
        trade_updates = []

        if order.exchange_order_id is not None:
            exchange_order_id = int(order.exchange_order_id)
            # trading_pair = await self.exchange_symbol_associated_to_pair(trading_pair=order.trading_pair)

            all_fills_response = [x for x in all_orders_fills_response if x["orderId"] == exchange_order_id]

            for trade in all_fills_response:

                if order.trade_type == TradeType.BUY:
                    commission_asset = self._convert_trading_pair_naming_mapping(trade["srcCurrency"])
                else:
                    commission_asset = self._convert_trading_pair_naming_mapping(trade["dstCurrency"])

                commission_amount = Decimal(trade["fee"])

                if commission_asset == "RLS":
                    commission_asset = "IRT"
                    commission_amount = commission_amount / 10

                fee = TradeFeeBase.new_spot_fee(
                    fee_schema=self.trade_fee_schema(),
                    trade_type=order.trade_type,
                    percent_token=commission_asset,
                    flat_fees=[TokenAmount(amount=commission_amount, token=commission_asset)],
                )

                trade_update = TradeUpdate(
                    trade_id=str(trade["id"]),
                    client_order_id=order.client_order_id,
                    exchange_order_id=str(exchange_order_id),
                    trading_pair=order.trading_pair,
                    fee=fee,
                    fill_base_amount=Decimal(trade["amount"]),
                    fill_quote_amount=Decimal(trade["amount"]) * Decimal(trade["price"]),
                    fill_price=Decimal(trade["price"]),
                    fill_timestamp=time.time() * 1e-3,
                )
                trade_updates.append(trade_update)

        return trade_updates

    # TODO: First check done
    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        raise Exception("Developer: This method should not be called, it is obsoleted for Nobitex")

    # TODO: First check done
    async def _request_order_status(self, tracked_order: InFlightOrder) -> OrderUpdate:

        updated_order_data = await self._api_get(
            path_url=CONSTANTS.ORDER_STATUS_PATH_URL,
            params={"id": int(tracked_order.exchange_order_id), "clientOrderId": tracked_order.client_order_id},
            is_auth_required=True,
        )

        new_state = CONSTANTS.ORDER_STATE[updated_order_data["order"]["status"]]
        if new_state == OrderState.OPEN and updated_order_data["order"]["partial"]:
            new_state = OrderState.PARTIALLY_FILLED

        order_update = OrderUpdate(
            client_order_id=tracked_order.client_order_id,
            exchange_order_id=str(updated_order_data["order"]["id"]),
            trading_pair=tracked_order.trading_pair,
            update_timestamp=time.time() * 1e-3,
            new_state=new_state,
        )

        return order_update

    # TODO: First check done
    async def _update_balances(self):
        local_asset_names = set(self._account_balances.keys())
        remote_asset_names = set()

        account_info = await self._api_get(path_url=CONSTANTS.USER_WALLETS_PATH, is_auth_required=True)

        balances = account_info["wallets"]
        for balance_entry in balances:
            asset_name = str(balance_entry["currency"]).upper()

            free_balance = Decimal(balance_entry["activeBalance"])
            total_balance = Decimal(balance_entry["balance"])

            if asset_name == "RLS":
                asset_name = "IRT"
                free_balance = free_balance / 10
                total_balance = total_balance / 10

            self._account_available_balances[asset_name] = free_balance
            self._account_balances[asset_name] = total_balance
            remote_asset_names.add(asset_name)

        asset_names_to_remove = local_asset_names.difference(remote_asset_names)
        for asset_name in asset_names_to_remove:
            del self._account_available_balances[asset_name]
            del self._account_balances[asset_name]

    def _initialize_trading_pair_naming_dictionary(self, exchange_info: Dict[str, Any]):
        mapping = bidict()

        coins = exchange_info.get("coins", [])

        for c in coins:
            name = c.get("name")
            stdName = c.get("stdName", name)
            coin = c.get("coin").upper()

            mapping[stdName] = coin

        self._naming_dictionary = mapping

    def _convert_trading_pair_naming_mapping(self, stdName: str) -> str:
        return self._naming_dictionary.get(stdName)

    # TODO: First check done
    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]):

        self._initialize_trading_pair_naming_dictionary(exchange_info)

        mapping = bidict()

        nobitex_info = exchange_info.get("nobitex", {})
        amountPrecisions = nobitex_info.get("amountPrecisions", {})
        symbols = amountPrecisions.keys()

        for pair in symbols:
            if pair.upper().endswith("USDT"):
                quote = "USDT"
            elif pair.upper().endswith("IRT"):
                quote = "IRT"
            else:
                self.logger().warning(f"Error parsing the trading pair rule {pair}. Skipping.")
                continue

            base = pair.replace(quote, "").upper()

            mapping[pair] = combine_to_hb_trading_pair(base=base, quote=quote)

        self._set_trading_pair_symbol_map(mapping)

    async def _get_last_traded_price(self, trading_pair: str) -> float:

        symbol = await self.exchange_symbol_associated_to_pair(trading_pair=trading_pair)

        resp_json = await self._api_request(
            method=RESTMethod.GET, path_url=CONSTANTS.SNAPSHOT_PATH_URL + symbol, limit_id=CONSTANTS.SNAPSHOT_PATH_URL
        )

        if str(symbol).endswith("IRT"):
            lastPrice = Decimal(resp_json["lastTradePrice"]) / 10
        else:
            lastPrice = Decimal(resp_json["lastTradePrice"])

        return float(lastPrice)

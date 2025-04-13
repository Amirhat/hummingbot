import logging
import random
import statistics
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from hummingbot.client.performance import PerformanceMetrics
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.core.clock import Clock
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.event.events import MarketOrderFailureEvent, OrderCancelledEvent, OrderExpiredEvent
from hummingbot.logger import HummingbotLogger
from hummingbot.strategy.conditional_execution_state import ConditionalExecutionState, RunAlwaysExecutionState
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.strategy_py_base import StrategyPyBase

stealth_trader_logger = None


class StealthTraderStrategy(StrategyPyBase):
    """
    Stealth Trader strategy
    This strategy is intended for automating the detection and purchase of USDT at low prices.
    It randomizes order amounts to avoid detection and places orders within a specified price range.
    """

    @classmethod
    def logger(cls) -> HummingbotLogger:
        global stealth_trader_logger
        if stealth_trader_logger is None:
            stealth_trader_logger = logging.getLogger(__name__)
        return stealth_trader_logger

    def __init__(
        self,
        market_infos: List[MarketTradingPairTuple],
        is_buy: bool,
        target_asset_amount: Decimal,
        order_step_size: Decimal,
        price_lower_bound: Decimal,
        price_upper_bound: Decimal,
        order_lifetime: float = 60.0,
        randomization_percentage: Decimal = Decimal("0.1"),
        execution_state: ConditionalExecutionState = None,
        cancel_order_wait_time: Optional[float] = 60.0,
        status_report_interval: float = 900,
    ):
        """
        :param market_infos: list of market trading pairs
        :param is_buy: if the order is to buy
        :param target_asset_amount: total qty of the asset to trade
        :param order_step_size: base amount for each order (will be randomized)
        :param price_lower_bound: lower bound of the price range (P1)
        :param price_upper_bound: upper bound of the price range (P2)
        :param order_lifetime: how long an order should live before being canceled
        :param randomization_percentage: percentage to randomize the order amount (0.1 = 10%)
        :param execution_state: execution state object with the conditions that should be satisfied to run each tick
        :param cancel_order_wait_time: how long to wait before canceling an order
        :param status_report_interval: how often to report network connection related warnings, if any
        """

        if len(market_infos) < 1:
            raise ValueError("market_infos must not be empty.")

        super().__init__()
        self._market_infos = {
            (market_info.market, market_info.trading_pair): market_info for market_info in market_infos
        }
        self._all_markets_ready = False
        self._place_orders = True
        self._status_report_interval = status_report_interval
        self._order_lifetime = order_lifetime
        self._quantity_remaining = target_asset_amount
        self._time_to_cancel = {}
        self._is_buy = is_buy
        self._target_asset_amount = target_asset_amount
        self._order_step_size = order_step_size
        self._price_lower_bound = price_lower_bound
        self._price_upper_bound = price_upper_bound
        self._randomization_percentage = randomization_percentage
        self._last_order_timestamp = 0
        self._last_timestamp = 0
        self._execution_state = execution_state or RunAlwaysExecutionState()

        if cancel_order_wait_time is not None:
            self._cancel_order_wait_time = cancel_order_wait_time

        all_markets = set([market_info.market for market_info in market_infos])
        self.add_markets(list(all_markets))

    @property
    def active_bids(self) -> List[Tuple[ExchangeBase, LimitOrder]]:
        return self.order_tracker.active_bids

    @property
    def active_asks(self) -> List[Tuple[ExchangeBase, LimitOrder]]:
        return self.order_tracker.active_asks

    @property
    def active_limit_orders(self) -> List[Tuple[ExchangeBase, LimitOrder]]:
        return self.order_tracker.active_limit_orders

    @property
    def in_flight_cancels(self) -> Dict[str, float]:
        return self.order_tracker.in_flight_cancels

    @property
    def market_info_to_active_orders(self) -> Dict[MarketTradingPairTuple, List[LimitOrder]]:
        return self.order_tracker.market_pair_to_active_orders

    @property
    def place_orders(self):
        return self._place_orders

    def configuration_status_lines(
        self,
    ):
        lines = ["", "  Configuration:"]

        for market_info in self._market_infos.values():
            lines.append(
                "    "
                f"Total amount: {PerformanceMetrics.smart_round(self._target_asset_amount)} "
                f"{market_info.base_asset}    "
                f"Price range: {PerformanceMetrics.smart_round(self._price_lower_bound)} - "
                f"{PerformanceMetrics.smart_round(self._price_upper_bound)} "
                f"{market_info.quote_asset}    "
                f"Base order size: {PerformanceMetrics.smart_round(self._order_step_size)} "
                f"{market_info.base_asset}"
            )

        lines.append(f"    Execution type: {self._execution_state}")

        return lines

    def filled_trades(self):
        """
        Returns a list of all filled trades generated from limit orders with the same trade type the strategy
        has in its configuration
        """
        trade_type = TradeType.BUY if self._is_buy else TradeType.SELL
        return [
            trade
            for trade in self.trades
            if trade.trade_type == trade_type.name and trade.order_type == OrderType.LIMIT
        ]

    def format_status(self) -> str:
        lines: list = []
        warning_lines: list = []

        lines.extend(self.configuration_status_lines())

        for market_info in self._market_infos.values():

            active_orders = self.market_info_to_active_orders.get(market_info, [])

            warning_lines.extend(self.network_warning([market_info]))

            markets_df = self.market_status_data_frame([market_info])
            lines.extend(["", "  Markets:"] + ["    " + line for line in markets_df.to_string().split("\n")])

            assets_df = self.wallet_balance_data_frame([market_info])
            lines.extend(["", "  Assets:"] + ["    " + line for line in assets_df.to_string().split("\n")])

            # See if there're any open orders.
            if len(active_orders) > 0:
                price_provider = None
                for market_info in self._market_infos.values():
                    price_provider = market_info
                if price_provider is not None:
                    df = LimitOrder.to_pandas(active_orders, mid_price=float(price_provider.get_mid_price()))
                    if self._is_buy:
                        # Descend from the price closest to the mid price
                        df = df.sort_values(by=["Price"], ascending=False)
                    else:
                        # Ascend from the price closest to the mid price
                        df = df.sort_values(by=["Price"], ascending=True)
                    df = df.reset_index(drop=True)
                    df_lines = df.to_string().split("\n")
                    lines.extend(["", "  Active orders:"] + ["    " + line for line in df_lines])
            else:
                lines.extend(["", "  No active maker orders."])

            filled_trades = self.filled_trades()
            average_price = statistics.mean([trade.price for trade in filled_trades]) if filled_trades else Decimal(0)
            lines.extend(
                [
                    "",
                    f"  Average filled orders price: "
                    f"{PerformanceMetrics.smart_round(average_price)} "
                    f"{market_info.quote_asset}",
                ]
            )

            lines.extend(
                [
                    f"  Pending amount: {PerformanceMetrics.smart_round(self._quantity_remaining)} "
                    f"{market_info.base_asset}"
                ]
            )

            warning_lines.extend(self.balance_warning([market_info]))

        if warning_lines:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)

        return "\n".join(lines)

    def did_fill_order(self, order_filled_event):
        """
        Output log for filled order.
        :param order_filled_event: Order filled event
        """
        order_id: str = order_filled_event.order_id
        market_info = self.order_tracker.get_shadow_market_pair_from_order_id(order_id)

        if market_info is not None:
            self.log_with_clock(
                logging.INFO,
                f"({market_info.trading_pair}) Limit {order_filled_event.trade_type.name.lower()} order of "
                f"{order_filled_event.amount} {market_info.base_asset} filled.",
            )

    def did_complete_buy_order(self, order_completed_event):
        """
        Output log for completed buy order.
        :param order_completed_event: Order completed event
        """
        self.log_complete_order(order_completed_event)

    def did_complete_sell_order(self, order_completed_event):
        """
        Output log for completed sell order.
        :param order_completed_event: Order completed event
        """
        self.log_complete_order(order_completed_event)

    def log_complete_order(self, order_completed_event):
        """
        Output log for completed order.
        :param order_completed_event: Order completed event
        """
        order_id: str = order_completed_event.order_id
        market_info = self.order_tracker.get_market_pair_from_order_id(order_id)

        if market_info is not None:
            limit_order_record = self.order_tracker.get_limit_order(market_info, order_id)
            order_type = "buy" if limit_order_record.is_buy else "sell"
            self.log_with_clock(
                logging.INFO,
                f"({market_info.trading_pair}) Limit {order_type} order {order_id} "
                f"({limit_order_record.quantity} {limit_order_record.base_currency} @ "
                f"{limit_order_record.price} {limit_order_record.quote_currency}) has been filled.",
            )

    def did_cancel_order(self, cancelled_event: OrderCancelledEvent):
        self.update_remaining_after_removing_order(cancelled_event.order_id, "cancel")

    def did_fail_order(self, order_failed_event: MarketOrderFailureEvent):
        self.update_remaining_after_removing_order(order_failed_event.order_id, "fail")

    def did_expire_order(self, expired_event: OrderExpiredEvent):
        self.update_remaining_after_removing_order(expired_event.order_id, "expire")

    def update_remaining_after_removing_order(self, order_id: str, event_type: str):
        market_info = self.order_tracker.get_market_pair_from_order_id(order_id)
        if market_info is not None:
            limit_order_record = self.order_tracker.get_limit_order(market_info, order_id)
            if limit_order_record is not None:
                self._quantity_remaining += limit_order_record.quantity
                self.log_with_clock(
                    logging.INFO, f"Order {order_id} {event_type}led. Remaining amount: {self._quantity_remaining}"
                )

    def process_market(self, market_info):
        """
        Check if market is ready and process the market.
        :param market_info: MarketTradingPairTuple
        """
        market_ready = market_info.market.ready
        if not market_ready:
            self.log_with_clock(logging.WARNING, f"{market_info.market.name} is not ready. Please wait...")
            return

        if self._place_orders:
            self.place_orders_for_market(market_info)

    def start(self, clock: Clock, timestamp: float):
        self._last_order_timestamp = timestamp
        super().start(clock, timestamp)

    def tick(self, timestamp: float):
        """
        Clock tick entry point.
        :param timestamp: current tick timestamp
        """

        try:
            self._execution_state.process_tick(timestamp, self)
        finally:
            self._last_timestamp = timestamp

    def process_tick(self, timestamp: float):
        """
        Process the tick and check if orders need to be canceled or if new orders need to be created.
        :param timestamp: current tick timestamp
        """
        if not self._all_markets_ready:
            self._all_markets_ready = all([market.ready for market in self.active_markets])
            if not self._all_markets_ready:
                return

        for market_info in self._market_infos.values():

            active_limit_orders = self.active_limit_orders
            for active_order in active_limit_orders:
                if (
                    active_order[1].client_order_id in self._time_to_cancel
                    and self._time_to_cancel[active_order[1].client_order_id] < timestamp
                ):
                    self.cancel_order(market_info, active_order[1].client_order_id)
                    del self._time_to_cancel[active_order[1].client_order_id]

            self.process_market(market_info)

    def cancel_active_orders(self):
        # Nothing to do here
        pass

    def place_orders_for_market(self, market_info):
        """
        Place orders for the market.
        :param market_info: MarketTradingPairTuple
        """
        if self._quantity_remaining <= Decimal("0"):
            return

        # Calculate the randomized order amount
        base_amount = min(self._order_step_size, self._quantity_remaining)
        randomization_factor = Decimal(1) + (
            Decimal(random.uniform(-float(self._randomization_percentage), float(self._randomization_percentage)))
        )
        order_amount = base_amount * randomization_factor
        order_amount = min(order_amount, self._quantity_remaining)

        # Ensure the order amount meets the exchange's minimum requirements
        quantized_amount = market_info.market.quantize_order_amount(market_info.trading_pair, order_amount)

        if quantized_amount == Decimal("0"):
            self.log_with_clock(
                logging.WARNING,
                f"Order amount {order_amount} is too small. Minimum order amount is "
                f"{market_info.market.get_min_order_amount(market_info.trading_pair)}.",
            )
            return

        # Generate a random price within the specified range
        price_range = self._price_upper_bound - self._price_lower_bound
        random_price_offset = Decimal(random.random()) * price_range
        order_price = self._price_lower_bound + random_price_offset

        # Ensure the price meets the exchange's requirements
        quantized_price = market_info.market.quantize_order_price(market_info.trading_pair, order_price)

        trading_rule = market_info.market._trading_rules[market_info.trading_pair]
        min_notional_size = trading_rule.min_notional_size

        # If the remaining quantity is less than the minimum notional size, use the remaining quantity
        # Otherwise, use the quantized amount
        # it is avoid to place a next order with a notional size less than the minimum notional size

        if (self._quantity_remaining - quantized_amount) * quantized_price < min_notional_size:
            quantized_amount = market_info.market.quantize_order_amount(
                market_info.trading_pair, self._quantity_remaining
            )
            sub_amount = self._quantity_remaining
        else:
            sub_amount = quantized_amount

        if self.has_enough_balance(market_info, quantized_amount):
            self._quantity_remaining -= sub_amount
            if not self._is_buy:
                order_id = self.sell_with_specific_market(
                    market_info, quantized_amount, order_type=OrderType.LIMIT, price=quantized_price
                )
                self._time_to_cancel[order_id] = self._last_timestamp + self._order_lifetime
                self.log_with_clock(
                    logging.INFO,
                    f"Submitting {TradeType.SELL.name} order for {quantized_amount} {market_info.base_asset} at "
                    f"{quantized_price} {market_info.quote_asset}.",
                )

            else:
                order_id = self.buy_with_specific_market(
                    market_info, quantized_amount, order_type=OrderType.LIMIT, price=quantized_price
                )
                self._time_to_cancel[order_id] = self._last_timestamp + self._order_lifetime
                self.log_with_clock(
                    logging.INFO,
                    f"Submitting {TradeType.BUY.name} order for {quantized_amount} {market_info.base_asset} at "
                    f"{quantized_price} {market_info.quote_asset}.",
                )
        else:
            self.log_with_clock(
                logging.WARNING, f"Not enough balance to submit order for {quantized_amount} {market_info.base_asset}."
            )

    def has_enough_balance(self, market_info, amount: Decimal) -> bool:
        """
        Check if there is enough balance to place an order.
        :param market_info: MarketTradingPairTuple
        :param amount: order amount
        :return: True if there is enough balance, False otherwise
        """

        market: ExchangeBase = market_info.market
        base_asset_balance = market.get_balance(market_info.base_asset)
        quote_asset_balance = market.get_balance(market_info.quote_asset)
        order_book: OrderBook = market_info.order_book
        price = order_book.get_price_for_volume(True, float(amount)).result_price

        return quote_asset_balance >= (amount * Decimal(price)) if self._is_buy else base_asset_balance >= amount

    def calculate_commission(self, market_info, amount: Decimal, price: Decimal) -> Decimal:
        """
        Calculate the commission for a trade.
        :param market_info: MarketTradingPairTuple
        :param amount: order amount
        :param price: order price
        :return: commission amount
        """
        exchange_fee = market_info.market.get_fee(
            market_info.base_asset,
            market_info.quote_asset,
            OrderType.LIMIT,
            TradeType.BUY if self._is_buy else TradeType.SELL,
            amount,
            price,
        )
        return exchange_fee.percent * amount * price

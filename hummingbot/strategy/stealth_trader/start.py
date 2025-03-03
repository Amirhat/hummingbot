from datetime import datetime
from typing import List, Tuple

from hummingbot.strategy.conditional_execution_state import RunAlwaysExecutionState, RunInTimeConditionalExecutionState
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.stealth_trader import StealthTraderStrategy
from hummingbot.strategy.stealth_trader.stealth_trader_config_map import stealth_trader_config_map


def start(self):
    try:
        order_step_size = stealth_trader_config_map.get("order_step_size").value
        trade_side = stealth_trader_config_map.get("trade_side").value
        target_asset_amount = stealth_trader_config_map.get("target_asset_amount").value
        is_delayed_start_execution = stealth_trader_config_map.get("is_delayed_start_execution").value
        exchange = stealth_trader_config_map.get("connector").value.lower()
        raw_market_trading_pair = stealth_trader_config_map.get("trading_pair").value
        price_lower_bound = stealth_trader_config_map.get("price_lower_bound").value
        price_upper_bound = stealth_trader_config_map.get("price_upper_bound").value
        order_lifetime = stealth_trader_config_map.get("order_lifetime").value
        randomization_percentage = stealth_trader_config_map.get("randomization_percentage").value
        cancel_order_wait_time = stealth_trader_config_map.get("cancel_order_wait_time").value

        try:
            assets: Tuple[str, str] = self._initialize_market_assets(exchange, [raw_market_trading_pair])[0]
        except ValueError as e:
            self.notify(str(e))
            return

        market_names: List[Tuple[str, List[str]]] = [(exchange, [raw_market_trading_pair])]

        self._initialize_markets(market_names)
        maker_data = [self.markets[exchange], raw_market_trading_pair] + list(assets)
        self.market_trading_pair_tuples = [MarketTradingPairTuple(*maker_data)]

        is_buy = trade_side == "buy"

        if is_delayed_start_execution:
            start_datetime_string = stealth_trader_config_map.get("start_datetime").value
            start_time = datetime.fromisoformat(start_datetime_string)
            execution_state = RunInTimeConditionalExecutionState(start_timestamp=start_time)
        else:
            execution_state = RunAlwaysExecutionState()

        self.strategy = StealthTraderStrategy(
            market_infos=[MarketTradingPairTuple(*maker_data)],
            is_buy=is_buy,
            target_asset_amount=target_asset_amount,
            order_step_size=order_step_size,
            price_lower_bound=price_lower_bound,
            price_upper_bound=price_upper_bound,
            order_lifetime=order_lifetime,
            randomization_percentage=randomization_percentage,
            execution_state=execution_state,
            cancel_order_wait_time=cancel_order_wait_time,
        )
    except Exception as e:
        self.notify(str(e))
        self.logger().error("Unknown error during initialization.", exc_info=True)

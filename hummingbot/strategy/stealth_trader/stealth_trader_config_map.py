from decimal import Decimal
from typing import Optional

from hummingbot.client.config.config_validators import (
    validate_bool,
    validate_datetime_iso_string,
    validate_decimal,
    validate_exchange,
    validate_market_trading_pair,
)
from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.settings import AllConnectorSettings, required_exchanges
from hummingbot.connector.utils import split_hb_trading_pair


def trading_pair_prompt():
    exchange = stealth_trader_config_map.get("connector").value
    example_pairs = AllConnectorSettings.get_example_pairs().get(exchange)
    return "Enter the token trading pair you would like to trade on %s%s >>> " % (
        exchange,
        f" (e.g. {example_pairs})" if example_pairs else "",
    )


def target_asset_amount_prompt():
    trading_pair = stealth_trader_config_map.get("trading_pair").value
    base_token, _ = split_hb_trading_pair(trading_pair)

    return f"What is the total amount of {base_token} to be traded? (Default is 1.0) >>> "


def str2bool(value: str):
    return str(value).lower() in ("yes", "y", "true", "t", "1")


# checks if the trading pair is valid
def validate_market_trading_pair_tuple(value: str) -> Optional[str]:
    exchange = stealth_trader_config_map.get("connector").value
    return validate_market_trading_pair(exchange, value)


def validate_price_bounds(value: str = None):
    """
    Validates that the lower price bound is less than the upper price bound
    """
    result = validate_decimal(value, min_value=Decimal("0"), inclusive=False)
    if result is not None:
        return result

    # Only check if both values are set
    if "price_lower_bound" in stealth_trader_config_map and "price_upper_bound" in stealth_trader_config_map:
        lower_bound = stealth_trader_config_map.get("price_lower_bound").value
        upper_bound = stealth_trader_config_map.get("price_upper_bound").value

        # Skip validation if either value is not set yet
        if lower_bound is None or upper_bound is None:
            return None

        if Decimal(lower_bound) >= Decimal(upper_bound):
            return "Lower price bound must be less than upper price bound."

    return None


def validate_order_step_size(value: str = None):
    """
    Invalidates non-decimal input and checks if order_step_size is less than the target_asset_amount value
    :param value: User input for order_step_size parameter
    :return: Error message printed in output pane
    """
    result = validate_decimal(value, min_value=Decimal("0"), inclusive=False)
    if result is not None:
        return result
    target_asset_amount = stealth_trader_config_map.get("target_asset_amount").value
    if Decimal(value) > target_asset_amount:
        return "Order step size cannot be greater than the total trade amount."


stealth_trader_config_map = {
    "strategy": ConfigVar(key="strategy", prompt=None, default="stealth_trader"),
    "connector": ConfigVar(
        key="connector",
        prompt="Enter the name of spot connector >>> ",
        validator=validate_exchange,
        on_validated=lambda value: required_exchanges.add(value),
        prompt_on_new=True,
    ),
    "trading_pair": ConfigVar(
        key="trading_pair", prompt=trading_pair_prompt, validator=validate_market_trading_pair_tuple, prompt_on_new=True
    ),
    "trade_side": ConfigVar(
        key="trade_side",
        prompt="What operation will be executed? (buy/sell) >>> ",
        type_str="str",
        validator=lambda v: None if v in {"buy", "sell", ""} else "Invalid operation type.",
        default="buy",
        prompt_on_new=True,
    ),
    "target_asset_amount": ConfigVar(
        key="target_asset_amount",
        prompt=target_asset_amount_prompt,
        default=1.0,
        type_str="decimal",
        validator=lambda v: validate_decimal(v, min_value=Decimal("0"), inclusive=False),
        prompt_on_new=True,
    ),
    "order_step_size": ConfigVar(
        key="order_step_size",
        prompt="What is the base amount of each individual order (denominated in the base asset, default is 1)? "
        ">>> ",
        default=1.0,
        type_str="decimal",
        validator=validate_order_step_size,
        prompt_on_new=True,
    ),
    "price_lower_bound": ConfigVar(
        key="price_lower_bound",
        prompt="What is the lower bound of the price range (P1)? >>> ",
        type_str="decimal",
        validator=validate_price_bounds,
        prompt_on_new=True,
    ),
    "price_upper_bound": ConfigVar(
        key="price_upper_bound",
        prompt="What is the upper bound of the price range (P2)? >>> ",
        type_str="decimal",
        validator=validate_price_bounds,
        prompt_on_new=True,
    ),
    "order_lifetime": ConfigVar(
        key="order_lifetime",
        prompt="How long should each order be active before being canceled (in seconds)? >>> ",
        type_str="float",
        default=60.0,
        validator=lambda v: validate_decimal(v, min_value=Decimal("0"), inclusive=False),
        prompt_on_new=True,
    ),
    "randomization_percentage": ConfigVar(
        key="randomization_percentage",
        prompt="What percentage of randomization should be applied to order amounts (e.g., 0.1 for 10%)? >>> ",
        type_str="decimal",
        default=0.1,
        validator=lambda v: validate_decimal(v, min_value=Decimal("0"), max_value=Decimal("1"), inclusive=True),
        prompt_on_new=True,
    ),
    "is_delayed_start_execution": ConfigVar(
        key="is_delayed_start_execution",
        prompt="Do you want to specify a start time for the execution? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool,
        prompt_on_new=True,
    ),
    "start_datetime": ConfigVar(
        key="start_datetime",
        prompt="Please enter the start date and time" " (YYYY-MM-DD HH:MM:SS) >>> ",
        type_str="str",
        validator=validate_datetime_iso_string,
        required_if=lambda: stealth_trader_config_map.get("is_delayed_start_execution").value,
        prompt_on_new=True,
    ),
    "cancel_order_wait_time": ConfigVar(
        key="cancel_order_wait_time",
        prompt="How long do you want to wait before forcibly canceling your limit order (in seconds). "
        "(Default is 60 seconds) ? >>> ",
        type_str="float",
        default=60,
        validator=lambda v: validate_decimal(v, 0, inclusive=False),
        prompt_on_new=True,
    ),
}

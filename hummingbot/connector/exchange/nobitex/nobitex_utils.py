from decimal import Decimal

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "BTCUSDT"

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.002"),
    taker_percent_fee_decimal=Decimal("0.0025"),
    buy_percent_fee_deducted_from_returns=True,
)


# TODO: check if this is correct
# def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
#     """
#     Verifies if a trading pair is enabled to operate with based on its exchange information
#     :param exchange_info: the exchange information for a trading pair
#     :return: True if the trading pair is enabled, False otherwise
#     """
#     is_spot = False
#     is_trading = False

#     if exchange_info.get("status", None) == "TRADING":
#         is_trading = True

#     permissions_sets = exchange_info.get("permissionSets", list())
#     for permission_set in permissions_sets:
#         # PermissionSet is a list, find if in this list we have "SPOT" value or not
#         if "SPOT" in permission_set:
#             is_spot = True
#             break

#     return is_trading and is_spot


class NobitexConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="nobitex", const=True, client_data=None)

    nobitex_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Nobitex API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )
    # nobitex_api_secret: SecretStr = Field(
    #     default=...,
    #     client_data=ClientFieldData(
    #         prompt=lambda cm: "Enter your Nobitex API secret",
    #         is_secure=True,
    #         is_connect_key=True,
    #         prompt_on_new=True,
    #     )
    # )

    class Config:
        title = "nobitex"


KEYS = NobitexConfigMap.construct()

OTHER_DOMAINS = []
OTHER_DOMAINS_PARAMETER = {}
OTHER_DOMAINS_EXAMPLE_PAIR = {}
OTHER_DOMAINS_DEFAULT_FEES = {}

# OTHER_DOMAINS = ["nobitex_testnet"]
# OTHER_DOMAINS_PARAMETER = {"nobitex_testnet": "testnet"}
# OTHER_DOMAINS_EXAMPLE_PAIR = {"nobitex_testnet": "BTCUSDT"}
# OTHER_DOMAINS_DEFAULT_FEES = {"nobitex_testnet": DEFAULT_FEES}


# class NobitexTestnetConfigMap(BaseConnectorConfigMap):
#     connector: str = Field(default="nobitex_testnet", const=True, client_data=None)

#     nobitex_api_key: SecretStr = Field(
#         default=...,
#         client_data=ClientFieldData(
#             prompt=lambda cm: "Enter your Nobitex API key",
#             is_secure=True,
#             is_connect_key=True,
#             prompt_on_new=True,
#         )
#     )

#     class Config:
#         title = "nobitex_testnet"


# OTHER_DOMAINS_KEYS = {"nobitex_testnet": NobitexTestnetConfigMap.construct()}

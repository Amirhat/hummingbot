import time
from typing import Callable, Optional

import hummingbot.connector.exchange.nobitex.nobitex_constants as CONSTANTS
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


def public_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for provided public REST endpoint
    :param path_url: a public REST endpoint
    :param domain: the Nobitex domain to connect to ("nobitex_main" or "nobitex_testnet"). The default value is "nobitex_main"
    :return: the full URL to the endpoint
    """
    return CONSTANTS.REST_URLS[domain] + path_url


def private_rest_url(path_url: str, domain: str = CONSTANTS.DEFAULT_DOMAIN) -> str:
    """
    Creates a full URL for provided private REST endpoint
    :param path_url: a private REST endpoint
    :param domain: the Nobitex domain to connect to ("nobitex_main" or "nobitex_testnet"). The default value is "nobitex_main"
    :return: the full URL to the endpoint
    """
    return CONSTANTS.REST_URLS[domain] + path_url


def build_api_factory(
    throttler: Optional[AsyncThrottler] = None,
    _time_synchronizer: Optional[TimeSynchronizer] = None,
    _domain: str = CONSTANTS.DEFAULT_DOMAIN,
    _time_provider: Optional[Callable] = None,
    auth: Optional[AuthBase] = None,
) -> WebAssistantsFactory:
    throttler = throttler or create_throttler()

    api_factory = WebAssistantsFactory(throttler=throttler, auth=auth)

    # rest_pre_processors=None  #[
    #    TimeSynchronizerRESTPreProcessor(synchronizer=time_synchronizer, time_provider=time_provider),
    # ])
    return api_factory


def build_api_factory_without_time_synchronizer_pre_processor(throttler: AsyncThrottler) -> WebAssistantsFactory:
    api_factory = WebAssistantsFactory(throttler=throttler)
    return api_factory


def create_throttler() -> AsyncThrottler:
    return AsyncThrottler(CONSTANTS.RATE_LIMITS)


async def get_current_server_time(
    throttler: Optional[AsyncThrottler] = None,
    domain: str = CONSTANTS.DEFAULT_DOMAIN,
) -> int:
    """Get current server time in milliseconds.

    Args:
        throttler (Optional[AsyncThrottler], optional): Throttler instance. Defaults to None.
        domain (str, optional): Nobitex domain. Defaults to CONSTANTS.DEFAULT_DOMAIN.

    Returns:
        int: Current server time in milliseconds.

    This is similar to ascend_ex get_current_server_time function.
    """
    return int(time.time() * 1e3)

import random
import string
import time
from typing import Callable, Optional

import hummingbot.connector.exchange.nobitex.nobitex_constants as CONSTANTS
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest
from hummingbot.core.web_assistant.rest_pre_processors import RESTPreProcessorBase
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class NobitexRESTPreProcessor(RESTPreProcessorBase):
    async def pre_process(self, request: RESTRequest) -> RESTRequest:
        if request.headers is None:
            request.headers = {}

        headers_generic = {}
        random_XXXXX = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        random_XXXXX = "TraderBot/" + random_XXXXX  # or "TraderBot/HUMING"
        headers_generic["user-agent"] = random_XXXXX

        request.headers = dict(
            list(request.headers.items()) + list(headers_generic.items())
        )
        return request


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

    rest_pre_processors = [
        NobitexRESTPreProcessor(),
    ]

    api_factory = WebAssistantsFactory(throttler=throttler, auth=auth, rest_pre_processors=rest_pre_processors)

    # rest_pre_processors=None  #[
    #    TimeSynchronizerRESTPreProcessor(synchronizer=time_synchronizer, time_provider=time_provider),
    # ])
    return api_factory


def build_api_factory_without_time_synchronizer_pre_processor(throttler: AsyncThrottler) -> WebAssistantsFactory:
    rest_pre_processors = [
        NobitexRESTPreProcessor(),
    ]
    api_factory = WebAssistantsFactory(throttler=throttler, rest_pre_processors=rest_pre_processors)
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

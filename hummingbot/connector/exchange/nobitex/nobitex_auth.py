from typing import Any, Dict

from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.web_assistant.auth import AuthBase
from hummingbot.core.web_assistant.connections.data_types import RESTRequest, WSRequest


class NobitexAuth(AuthBase):
    def __init__(self, api_key: str, time_provider: TimeSynchronizer):
        self.api_key = api_key
        self.time_provider = time_provider

    # TODO: First check done
    async def rest_authenticate(self, request: RESTRequest) -> RESTRequest:
        """
        Adds the server time and the signature to the request, required for authenticated interactions. It also adds
        the required parameter in the request header.
        :param request: the request to be configured for authenticated interaction
        """

        headers = {}
        if request.headers is not None:
            headers.update(request.headers)
        headers.update(self.header_for_authentication())
        request.headers = headers

        return request

    # TODO: First check done
    async def ws_authenticate(self, request: WSRequest) -> WSRequest:
        """
        This method is intended to configure a websocket request to be authenticated. Nobitex does not use this
        functionality
        """
        return request  # pass-through

    # TODO: First check done
    def header_for_authentication(self) -> Dict[str, str]:
        return {"Authorization": f"Token {self.api_key}"}

    # TODO: First check done
    def add_auth_to_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return params

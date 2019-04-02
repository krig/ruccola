"""
Implements the Rocket.Chat REST API
"""
import requests
import json
import traceback


class APIError(IOError):
    """
    Exception raised on API call failure
    """
    def __init__(self, call="", payload=None, response=None):
        IOError.__init__(self, call)
        self.call = call
        self.payload = payload
        self.response = response


class Channel(object):
    """
    Describes a rocket.chat channel.
    """
    def __init__(self, session, res):
        self._session = session
        self.id = res["_id"]
        self.name = res["name"]

    def postMessage(self, text):
        """
        /api/v1/chat.postMessage
        text: Message to post
        """
        payload = {
                "roomId": self.id,
                "channel": "#{}".format(self.name),
                "text": text
        }
        return self._session.post("/api/v1/chat.postMessage", payload=payload)


class Session(object):
    def __init__(self, config):
        self._cfg = config
        self._headers = self._buildHeaders()

    def _buildHeaders(self):
        return {
                "X-Auth-Token": self._cfg.token,
                "X-User-Id": self._cfg.user_id,
                "Content-Type": "application/json"
        }

    def get(self, call, payload=None):
        """
        Basic REST GET API call.
        
        call: endpoint to call (string)
        payload: data to pass (dict)
        
        Returns decoded JSON response if successful.
        Raises APIError on failure.
        """
        data = json.dumps(payload) if payload else None
        response = requests.get(
            "https://{server}{call}".format(
                server=self._cfg.server, 
                call=call),
            headers=self._headers,
            data=data)
        resj = json.loads(response.text)
        if resj.get("success") is True:
            return resj
        raise APIError(call=call, payload=payload, response=response)

    def post(self, call, payload=None):
        """
        Basic REST POST API call.

        call: See get()
        payload: See get()

        Returns: See get()
        """
        data = json.dumps(payload) if payload else None
        response = requests.post(
            "https://{server}{call}".format(
                server=self._cfg.server, 
                call=call),
            headers=self._headers,
            data=data)
        resj = json.loads(response.text)
        if resj.get("success") is True:
            return resj
        raise APIError(call=call, payload=payload, response=response)

    def listJoinedChannels(self):
        """
        List channels user has joined.
        Returns [Channel]
        Raises APIError on failure.
        """
        response = self.get("/api/v1/channels.list.joined")
        return [Channel(self, channel) for channel in response["channels"]]



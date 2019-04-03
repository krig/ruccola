"""
Implements the Rocket.Chat REST API
"""
import requests
import json
import traceback
import asyncio
import websockets
from collections import namedtuple


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
        self.session = session
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
        return self.session.post("/api/v1/chat.postMessage", payload=payload)

    def history(self, latest=None, oldest=None, offset=0, count=20, unreads=False):
        """
        Retrieves historical messages from channel.
        """
        payload = { "roomId": self.id }
        if latest is not None:
            payload["latest"] = latest
        if oldest is not None:
            payload["oldest"] = oldest
        if offset > 0:
            payload["offset"] = offset
        if count != 20:
            payload["count"] = count
        if unreads:
            payload["unreads"] = True
        return self.session.get("/api/v1/channels.history", payload=payload)["messages"]

    def online(self):
        """
        Lists online users in channel.
        """
        payload = {"_id": self.id}
        return self.session.get("/api/v1/channels.online", payload=payload)["online"]


class Session(object):
    def __init__(self, config):
        self.config = config
        self._headers = self._buildHeaders()

    def _buildHeaders(self):
        return {
                "X-Auth-Token": self.config.token,
                "X-User-Id": self.config.user_id,
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
        from .app import dlog
        dlog("GET({})->{}".format(call, json.dumps(payload) if payload else ""))
        response = requests.get(
            "https://{server}{call}".format(
                server=self.config.server, 
                call=call),
            headers=self._headers,
            params=payload)
        dlog("GET({})<-{}".format(call, response.text))
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
        from .app import dlog
        dlog("POST({})->{}".format(call, json.dumps(payload) if payload else ""))
        response = requests.post(
            "https://{server}{call}".format(
                server=self.config.server, 
                call=call),
            headers=self._headers,
            data=payload)
        dlog("POST({})<-{}".format(call, response.text))
        resj = json.loads(response.text)
        if resj.get("success") is True:
            return resj
        raise APIError(call=call, payload=payload, response=response)

    def listChannels(self):
        """
        List all channels on server.
        Returns [Channel]
        Raises APIError on failure.
        """
        response = self.get("/api/v1/channels.list")
        return [Channel(self, channel) for channel in response["channels"]]

    def listJoinedChannels(self):
        """
        List channels user has joined.
        Returns [Channel]
        Raises APIError on failure.
        """
        response = self.get("/api/v1/channels.list.joined")
        return [Channel(self, channel) for channel in response["channels"]]

    def spotlight(self, query):
        """
        Searches for users or rooms that are visible to the user.
        Only returns rooms that the user hasn't joined yet.

        query: Term to search for.

        Returns the result of the search as a dict of two lists:
        "users" and "rooms".
        """
        return self.get("/api/v1/spotlight", payload={"query": query})

    def me(self):
        """
        Returns information about the user.

        Example result:

        {
          "_id": "aobEdbYhXfu5hkeqG",
          "name": "Example User",
          "emails": [
            {
              "address": "example@example.com",
              "verified": true
            }
          ],
          "status": "offline",
          "statusConnection": "offline",
          "username": "example",
          "utcOffset": 0,
          "active": true,
          "roles": [
            "user",
            "admin"
          ],
          "settings": {
            "preferences": {
              "enableAutoAway": false,
              "idleTimeoutLimit": 300,
              "desktopNotificationDuration": 0,
              "audioNotifications": "mentions",
              "desktopNotifications": "mentions",
              "mobileNotifications": "mentions",
              "unreadAlert": true,
              "useEmojis": true,
              "convertAsciiEmoji": true,
              "autoImageLoad": true,
              "saveMobileBandwidth": true,
              "collapseMediaByDefault": false,
              "hideUsernames": false,
              "hideRoles": false,
              "hideFlexTab": false,
              "hideAvatars": false,
              "roomsListExhibitionMode": "category",
              "sidebarViewMode": "medium",
              "sidebarHideAvatar": false,
              "sidebarShowUnread": false,
              "sidebarShowFavorites": true,
              "sendOnEnter": "normal",
              "messageViewMode": 0,
              "emailNotificationMode": "all",
              "roomCounterSidebar": false,
              "newRoomNotification": "door",
              "newMessageNotification": "chime",
              "muteFocusedConversations": true,
              "notificationsSoundVolume": 100
            }
          },
          "customFields": {
            "twitter": "@userstwi"
          },
          "success": true
        }
        """
        return self.get("/api/v1/me")


class Realtime(object):
    """
    WebSocket API for rocket.chat.
    """
    def __init__(self, config):
        self.config = config
        self._url = "wss://{server}/websocket".format(server=config.server)
        self._sendqueue = []
        self._recvqueue = []
        self._idgen = 0
        self._socket = None
        import logging
        self._logger = logging.getLogger('websockets')
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(logging.StreaHandler())

    def _send(self, **msg):
        data = json.dumps(msg)
        self._sendqueue.append(data)

    def _create_uid(self):
        self._idgen += 1
        return str(self._idgen)

    def call(self, method, *params):
        """
        Call a method on the server
        """
        uid = self._create_uid()
        self._send(msg="method", id=uid, method=method, params=list(params))
        return uid

    def subscribe(self, name, *params):
        """
        Subscribe to events
        """
        uid = self._create_uid()
        self._send(msg="sub", id=uid, name=name, params=list(params))
        return uid

    def unsubscribe(self, uid):
        """
        Unsubscribe from events
        """
        self._send(msg="unsub", id=uid)
        return uid

    def connect(self):
        """
        Connect to websocket and send initial connect message
        Returns the websocket mainloop coroutine
        """
        # push the connect message to the queue
        self._send(msg="connect", version="1", support=["1"])
        self._socket = websockets.connect(self._url, ssl=True)

        async def consumer_handler():
            while True:
                message = await self._socket.recv()
                self._recvqueue.append(message)

        async def producer_handler():
            while True:
                while not self._sendqueue:
                    asyncio.sleep(1)
                message = self._sendqueue.pop(0)
                await self._socket.send(message)
        
        async def mainloop():
            consumer_task = asyncio.ensure_future(consumer_handler())
            producer_task = asyncio.ensure_future(producer_handler())
            done, pending = await asyncio.wait([consumer_task, producer_task],
                    return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
        return mainloop

    def _mkmessage(self, obj):
        """
        Convert JSON object into a Message object
        """
        return namedtuple("Message", obj.keys())(*obj.values())

    def _mkroom(self, obj):
        """
        Convert JSON object into a Room object
        """
        return namedtuple("Room", obj.keys())(*obj.values())



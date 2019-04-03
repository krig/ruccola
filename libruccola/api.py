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
        return self._session.post("/api/v1/channels.history", payload=payload)["messages"]

    def online(self):
        """
        Lists online users in channel.
        """
        payload = {"_id": self.id}
        return self._session.get("/api/v1/channels.online", payload=payload)["online"]


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
        self._cfg = config
        self._url = "wss://{server}/websocket".format(server=config.server)


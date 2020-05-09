import aiohttp
import asyncio
import random
import string
import time
import typing
from pyryver.objects import *

class ClosedError(Exception):
    """
    An exception raised to indicate that the session has been closed.
    """

class RyverWS():
    """
    A live Ryver session using websockets. 
    """

    _VALID_ID_CHARS = string.ascii_letters + string.digits

    PRESENCE_AVAILABLE = "available"
    PRESENCE_AWAY = "away"
    PRESENCE_DO_NOT_DISTURB = "dnd"
    PRESENCE_OFFLINE = "unavailable"

    EVENT_REACTION_ADDED = "/api/reaction/added"
    EVENT_REACTION_REMOVED = "/api/reaction/removed"
    EVENT_ALL = ""

    MSG_TYPE_ALL = ""

    def __init__(self, ryver):
        self._ryver = ryver
        self._ws = None
        self._msg_ack_table = {}

        self._rx_task_handle = None
        self._ping_task_handle = None

        self._on_chat = None
        self._on_chat_deleted = None
        self._on_chat_updated = None
        self._on_connection_loss = None
        self._on_msg_type = {}
        self._on_event = {}

        self._closed = True
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc, *exc_info):
        await self.close()
    
    async def _ws_send_msg(self, msg: typing.Dict[str, typing.Any], timeout: float = None):
        """
        Send a message through the websocket.
        """
        if self._closed:
            raise ClosedError("Connection not started or already closed!")

        msg["id"] = RyverWS._create_id()
        # Put the future in the table to wait for ack
        key = (msg["id"], msg["type"])
        self._msg_ack_table[key] = asyncio.get_event_loop().create_future()
        # Send the data
        await self._ws.send_json(msg)

        try:
            # Wait for the ack with a timeout
            return await asyncio.wait_for(self._msg_ack_table[key], timeout)
        finally:
            # Remove the ack from the table if not already removed
            # This would only be true when the message timed out
            if key in self._msg_ack_table:
                self._msg_ack_table.pop(key)

    async def _rx_task(self):
        """
        This task receives data from the websocket.
        """
        try:
            while True:
                try:
                    msg = await self._ws.receive_json()
                    if msg["type"] == "ack":
                        # Find the message this ack is for
                        key = (msg["reply_to"], msg["reply_type"])
                        if key not in self._msg_ack_table:
                            print("Error: Received ack for a message not in table")
                        else:
                            # Remove from ack table
                            self._msg_ack_table[key].set_result(msg)
                            self._msg_ack_table.pop(key)
                    elif msg["type"] == "chat":
                        if self._on_chat:
                            asyncio.ensure_future(self._on_chat(msg))
                    elif msg["type"] == "chat_deleted":
                        if self._on_chat_deleted:
                            asyncio.ensure_future(self._on_chat_deleted(msg))
                    elif msg["type"] == "chat_updated":
                        if self._on_chat_updated:
                            asyncio.ensure_future(self._on_chat_updated(msg))
                    elif msg["type"] == "event":
                        handler = self._on_event.get(msg["topic"], self._on_event.get("", None))
                        if handler:
                            asyncio.ensure_future(handler(msg))
                    else:
                        handler = self._on_msg_type.get(msg["type"], self._on_msg_type.get("", None))
                        if handler:
                            asyncio.ensure_future(handler(msg))
                except ValueError as e:
                    print(f"Error decoding JSON message: {e}")
                except TypeError as e:
                    print(f"Error: Unexpected binary message received: {e}")
        except asyncio.CancelledError:
            return
    
    async def _ping_task(self):
        """
        This task sends a ping message once every few seconds to ensure the connection is alive.
        """
        try:
            while True:
                try:
                    # Send the ping
                    await self._ws_send_msg({
                        "type": "ping"
                    }, timeout=5.0)
                except asyncio.TimeoutError:
                    # Connection lost!
                    if self._on_connection_loss:
                        asyncio.ensure_future(self._on_connection_loss())
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            return
    
    def on_chat(self, func):
        """
        The on chat message coroutine decorator.

        This coroutine will be started as a task when a new chat message arrives.
        It should take a single argument, the chat message data.
        """
        self._on_chat = func

    def on_chat_deleted(self, func):
        """
        The on chat message deleted coroutine decorator.

        This coroutine will be started as a task when a chat message is deleted.
        It should take a single argument, the chat message data.
        """
        self._on_chat_deleted = func

    def on_chat_updated(self, func):
        """
        The on chat message updated coroutine decorator.

        This coroutine will be started as a task when a chat message is updated.
        It should take a single argument, the chat message data.
        """
        self._on_chat_updated = func
    
    def on_connection_loss(self, func):
        """
        The on connection loss coroutine decorator.

        This coroutine will be started as a task when the connection is lost.
        """
        self._on_connection_loss = func
    
    def on_event(self, event_type):
        """
        The on event coroutine decorator for a specific event or all unhandled
        events.

        This coroutine will be started as a task when a new event arrives with
        the specified type. If the event_type is None or an empty string, it will
        be called for all events that are unhandled.
        It should take a single argument, the event data.
        """
        if event_type is None:
            event_type = ""
        def _on_event_inner(func):
            self._on_event[event_type] = func
        return _on_event_inner
    
    def on_msg_type(self, msg_type):
        """
        The on message type coroutine decorator for a specific message type or all 
        unhandled messages.

        This coroutine will be started as a task when a new message arrives with
        the specified type. If the msg_type is None or an empty string, it will
        be called for all messages that are unhandled.
        It should take a single argument, the message data.
        """
        if msg_type is None:
            msg_type = ""
        def _on_msg_type_inner(func):
            self._on_msg_type[msg_type] = func
        return _on_msg_type_inner
    
    async def send_chat(self, to_chat: Chat, msg: str):
        """
        Send a chat message to a chat.
        """
        data = {
            "type": "chat",
            "to": to_chat.get_jid(),
            "text": msg
        }
        return await self._ws_send_msg(data)

    async def send_presence_change(self, presence: str):
        """
        Send a presence change message.
        """
        return await self._ws_send_msg({
            "type": "presence_change",
            "presence": presence,
        })
    
    async def send_typing(self, to_chat: Chat):
        """
        Send a typing indicator to a chat identified by JID.

        The typing indicator automatically clears after a few seconds or when
        a message is sent.
        """
        return await self._ws_send_msg({
            "type": "user_typing",
            "state": "composing",
            "to": to_chat.get_jid()
        })
    
    async def start(self):
        """
        Start the session.
        """
        url = self._ryver._url_prefix + "User.Login(client='pyryver')"
        async with self._ryver._session.post(url) as resp:
            login_info = (await resp.json())["d"]
        # Get the session ID for auth and the endpoint url
        session_id = login_info["sessionId"]
        chat_url = login_info["services"]["chat"]
        self._ws = await self._ryver._session.ws_connect(chat_url)

        self._closed = False
        # Start the rx and ping tasks
        self._rx_task_handle = asyncio.ensure_future(self._rx_task())
        self._ping_task_handle = asyncio.ensure_future(self._ping_task())
        # Authorize
        await self._ws_send_msg({
            "type": "auth",
            "authorization": "Session " + session_id,
            "agent": "Ryver",
            "resource": "Contatta-" + str(int(time.time() * 1000))
        })

    async def close(self):
        """
        Close the session.

        Any future operation after closing will result in a ClosedError being raised.
        """
        self._closed = True
        # Cancel all tasks
        self._ping_task_handle.cancel()
        self._rx_task_handle.cancel()
        await self._ws.close()
        # Terminate any messages waiting for acks with an exception
        for k, future in self._msg_ack_table.items():
            future.set_exception(ClosedError("Connection closed"))
        # Wait until tasks terminate
        await asyncio.gather(self._ping_task_handle, self._rx_task_handle)
    
    async def run_forever(self):
        """
        Run forever, or until the connection is closed.
        """
        await asyncio.gather(self._ping_task_handle, self._rx_task_handle)

    @staticmethod
    def _create_id():
        """
        Create a random message ID.
        """
        return "".join(random.choice(RyverWS._VALID_ID_CHARS) for x in range(9))
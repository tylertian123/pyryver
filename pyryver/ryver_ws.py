"""
This module contains the :py:class:`RyverWS` class, which allows you to respond to
messages in real-time.
"""

import asyncio
import json
import random
import string
import sys
import time
from aiohttp.http import WSMsgType
from . import doc
from .objects import *
from .ws_data import *


class ClosedError(Exception):
    """
    An exception raised to indicate that the session has been closed.
    """


class RyverWSTyping():
    """
    A context manager returned by :py:class:`RyverWS` to keep sending a typing
    indicator.

    You should not create this class yourself, rather use `RyverWS.start_typing()` instead.
    """

    def __init__(self, rws: "RyverWS", to: Chat):
        self._rws = rws
        self._to = to
        self._typing_task_handle = None

    async def _typing_task(self):
        """
        The task that keeps sending a typing indicator.
        """
        try:
            while True:
                await self._rws.send_typing(self._to)
                # Typing indicators clear after about 3 seconds
                await asyncio.sleep(2.5)
        except asyncio.CancelledError:
            await self._rws.send_clear_typing(self._to)

    def start(self):
        """
        Start sending the typing indicator.
        """
        self._typing_task_handle = asyncio.ensure_future(self._typing_task())

    async def stop(self):
        """
        Stop sending the typing indicator.

        .. note::
           This method will attempt to clear the typing indicator using
           :py:meth:`RyverWS.send_clear_typing()`. However, it only works in private
           messages. Outside of private messages, the typing indicator doesn't clear
           immediately. It will clear by itself after about 3 seconds, or when a message
           is sent. 
        """
        self._typing_task_handle.cancel()
        await asyncio.gather(self._typing_task_handle)

    async def __aenter__(self) -> "RyverWSTyping":
        self.start()
        return self

    async def __aexit__(self, exc, *exc_info):
        await self.stop()


class RyverWS():
    """
    A live Ryver session using websockets. 

    You can construct this manually, although it is recommended to use `Ryver.get_live_session()`.

    .. warning::
       This **does not work** when using a custom integration token to sign in.
    """

    _VALID_ID_CHARS = string.ascii_letters + string.digits

    #: "Available" presence (green).
    PRESENCE_AVAILABLE = "available"
    #: "Away" presence (yellow clock).
    PRESENCE_AWAY = "away"
    #: "Do Not Disturb" presence (red stop sign).
    PRESENCE_DO_NOT_DISTURB = "dnd"
    #: "Offline" presence (grey).
    PRESENCE_OFFLINE = "unavailable"

    #: A reaction was added to a message (includes topics, tasks and replies/comments).
    #:
    #: ``data`` field format:
    #:
    #: - ``"type"``: The entity type of the thing that was reacted to.
    #: - ``"id"``: The ID of the thing that was reacted to. String for chat messages,
    #:   int for everything else.
    #: - ``"userId"``: The ID of the user that reacted.
    #: - ``"reaction"``: The name of the emoji that the user reacted with.
    EVENT_REACTION_ADDED = "/api/reaction/added"
    #: A reaction was removed from a message (includes topics, tasks and replies/comments).
    #:
    #: ``data`` field format:
    #:
    #: - ``"type"``: The entity type of the thing that was reacted to.
    #: - ``"id"``: The ID of the thing that was reacted to. String for chat messages,
    #:   int for everything else.
    #: - ``"userId"``: The ID of the user that reacted.
    #: - ``"reaction"``: The name of the emoji that the user reacted with.
    EVENT_REACTION_REMOVED = "/api/reaction/removed"
    #: A topic was changed (created, updated, deleted).
    #:
    #: ``data`` field format:
    #:
    #: - ``"created"``: A list of objects containing data for topics that were newly created.
    #: - ``"updated"``: A list of objects containing data for topics that were updated.
    #: - ``"deleted"``: A list of objects containing data for topics that were deleted.
    EVENT_TOPIC_CHANGED = "/api/activityfeed/posts/changed"
    #: A task was changed (created, updated, deleted).
    #:
    #: ``data`` field format:
    #:
    #: - ``"created"``: A list of objects containing data for tasks that were newly created.
    #: - ``"updated"``: A list of objects containing data for tasks that were updated.
    #: - ``"deleted"``: A list of objects containing data for tasks that were deleted.
    EVENT_TASK_CHANGED = "/api/activityfeed/tasks/changed"
    #: Some entity was changed (created, updated, deleted).
    #:
    #: ``data`` field format:
    #:
    #: - ``"change"``: The type of the change, could be "created", "updated", or "deleted".
    #: - ``"entity"``: The entity that was changed and some of its data after the change.
    EVENT_ENTITY_CHANGED = "/api/entity/changed"
    #: All unhandled events.
    EVENT_ALL = ""

    #: A chat message was received.
    MSG_TYPE_CHAT = "chat"
    #: A chat message was updated.
    MSG_TYPE_CHAT_UPDATED = "chat_updated"
    #: A chat message was deleted.
    MSG_TYPE_CHAT_DELETED = "chat_deleted"
    #: A user changed their presence.
    MSG_TYPE_PRESENCE_CHANGED = "presence_change"
    #: A user is typing in a chat.
    MSG_TYPE_USER_TYPING = "user_typing"
    #: An event occurred.
    MSG_TYPE_EVENT = "event"
    #: All unhandled messages.
    MSG_TYPE_ALL = ""

    _HANDLER_DATA_TYPES = {
        MSG_TYPE_CHAT: WSChatMessageData,
        MSG_TYPE_CHAT_UPDATED: WSChatUpdatedData,
        MSG_TYPE_CHAT_DELETED: WSChatDeletedData,
        MSG_TYPE_PRESENCE_CHANGED: WSPresenceChangedData,
        MSG_TYPE_USER_TYPING: WSUserTypingData,
        MSG_TYPE_EVENT: WSEventData,
    }

    def __init__(self, ryver: "Ryver"):
        self._ryver = ryver
        self._ws = None
        self._msg_ack_table = {}

        self._rx_task_handle = None
        self._ping_task_handle = None

        self._on_connection_loss = None
        self._on_msg_type = {}
        self._on_event = {}

        self._closed = True

    async def __aenter__(self) -> "RyverWS":
        await self.start()
        return self

    async def __aexit__(self, exc, *exc_info):
        await self.close()

    def get_ryver(self) -> "Ryver":
        """
        Get the Ryver session this live session was created from.

        :return: The Ryver session this live session was created from.
        """
        return self._ryver

    async def _ws_send_msg(self, msg: typing.Dict[str, typing.Any], timeout: float = None) -> None:
        """
        Send a message through the websocket.

        An auto-generated message ID will be attached to the message to wait for acks.

        :param msg: The raw message data.
        :param timeout: The timeout for waiting for an ack. If None, waits forever.
        :raises ClosedError: If connection closed or not yet opened.    
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
                raw_msg = await self._ws.receive()
                if raw_msg.type != WSMsgType.TEXT:
                    if raw_msg.type is not None and raw_msg.type < 0x100:
                        sys.stderr.write(f"Warning: Wrong message type received, expected TEXT (0x1), got {raw_msg.type}. Message ignored.\n")
                    else:
                        sys.stderr.write(f"Error: Received unexpected aiohttp specific type for WS message: {raw_msg.type}. Killing connection.\n")
                        asyncio.ensure_future(self.close())
                        # Block to force a context switch and make sure connection is closed
                        await asyncio.sleep(0.2)
                else:
                    try:
                        msg = json.loads(raw_msg.data)
                    except json.JSONDecodeError as e:
                        sys.stderr.write(f"Warning: Received invalid JSON: {e}. Message ignored.\n")
                        continue
                    # Handle acks
                    if msg["type"] == "ack":
                        # Find the message this ack is for
                        key = (msg["reply_to"], msg["reply_type"])
                        if key not in self._msg_ack_table:
                            print("Error: Received ack for a message not in table")
                        else:
                            # Remove from ack table
                            self._msg_ack_table[key].set_result(msg)
                            self._msg_ack_table.pop(key)
                    # Handle events
                    elif msg["type"] == RyverWS.MSG_TYPE_EVENT and (msg["topic"] in self._on_event or "" in self._on_event):
                        # 
                        handler = self._on_event.get(msg["topic"]) or self._on_event.get("")
                        asyncio.ensure_future(handler(WSEventData(self._ryver, msg)))
                    # Handle all other message types
                    else:
                        handler = self._on_msg_type.get(msg["type"], self._on_msg_type.get("", None))
                        if handler:
                            # Get the correct data type
                            data_type = self._HANDLER_DATA_TYPES.get(msg["type"], WSMessageData)
                            asyncio.ensure_future(handler(data_type(self._ryver, msg)))
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

    def on_chat(self, func: typing.Callable[[WSChatMessageData], typing.Awaitable]):
        """
        Decorate a coroutine to be run when a new chat message is received.

        This coroutine will be started as a task when a new chat message arrives.
        It should take a single argument of type :py:class:`WSChatMessageData`, which
        contains the data for the message.
        """
        self._on_msg_type[RyverWS.MSG_TYPE_CHAT] = func
        return func

    def on_chat_deleted(self, func: typing.Callable[[WSChatDeletedData], typing.Awaitable]):
        """
        Decorate a coroutine to be run when a chat message is deleted.

        This coroutine will be started as a task when a chat message is deleted.
        It should take a single argument of type :py:class:`WSChatDeletedData`, which
        contains the data for the message.
        """
        self._on_msg_type[RyverWS.MSG_TYPE_CHAT_DELETED] = func
        return func

    def on_chat_updated(self, func: typing.Callable[[WSChatUpdatedData], typing.Awaitable]):
        """
        Decorate a coroutine to be run when a chat message is updated (edited).

        This coroutine will be started as a task when a chat message is updated.
        It should take a single argument of type :py:class:`WSChatUpdatedData`, which
        contains the data for the message.
        """
        self._on_msg_type[RyverWS.MSG_TYPE_CHAT_UPDATED] = func
        return func
    
    def on_presence_changed(self, func: typing.Callable[[WSPresenceChangedData], typing.Awaitable]):
        """
        Decorate a coroutine to be run when a user's presence changed.

        This coroutine will be started as a task when a user's presence changes.
        It should take a single argument of type :py:class:`WSPresenceChangedData`, which
        contains the data for the presence change.
        """
        self._on_msg_type[RyverWS.MSG_TYPE_PRESENCE_CHANGED] = func
        return func
    
    def on_user_typing(self, func: typing.Callable[[WSUserTypingData], typing.Awaitable]):
        """
        Decorate a coroutine to be run when a user starts typing.

        This coroutine will be started as a task when a user starts typing in a chat.
        It should take a single argument of type :py:class:`WSUserTypingData`, which
        contains the data for the user typing.
        """
        self._on_msg_type[RyverWS.MSG_TYPE_USER_TYPING] = func
        return func

    def on_connection_loss(self, func: typing.Callable[[], typing.Awaitable]):
        """
        Decorate a coroutine to be run when the connection is lost.

        This coroutine will be started as a task when the connection is lost.
        It should take no arguments.

        A connection loss is determined using a ping task. A ping is sent to Ryver once
        every 10 seconds, and if the response takes over 5 seconds, this coroutine will
        be started. (These numbers roughly match those used by the official web client.)

        Applications are suggested to clean up and terminate immediately when the
        connection is lost, especially when using :py:meth:`RyverWS.run_forever()`.
        A simple but typical implementation is shown below:

        .. code-block:: python
           async with ryver.get_live_session() as session:
               @session.on_connection_loss
               async def on_connection_loss():
                   await session.close()
        """
        self._on_connection_loss = func
        return func
    
    def on_error(self, func: typing.Callable[[typing.Union[TypeError, ValueError]], typing.Awaitable]):
        """
        Decorate a coroutine to be run when a connection error occurs. **No longer used.**

        .. deprecated:: 0.3.2
           This decorator is no longer used and currently does not do anything. Instead,
           when a non-recoverable error occurs, the connection will be closed
           automatically. Other errors (wrong message type, invalid JSON) will be
           ignored.
        """
        return func

    def on_event(self, event_type: str):
        """
        Decorate a coroutine to be run when an event occurs.

        This coroutine will be started as a task when a new event arrives with
        the specified type. If the ``event_type`` is None or an empty string, it will
        be called for all events that are unhandled.

        It should take a single argument of type :py:class:`WSEventData`, which
        contains the data for the event.

        :param event_type: The event type to listen to, one of the constants in 
                           this class starting with ``EVENT_`` or 
                           :py:attr:`RyverWS.EVENT_ALL` to receive all otherwise 
                           unhandled messages.
        """
        if event_type is None:
            event_type = ""

        def _on_event_inner(func: typing.Callable[[WSEventData], typing.Awaitable]):
            self._on_event[event_type] = func
            return func
        return _on_event_inner

    def on_msg_type(self, msg_type: str):
        """
        Decorate a coroutine to be run when for a type of websocket messages or for all
        unhandled messages.

        This coroutine will be started as a task when a new websocket message arrives
        with the specified type. If the ``msg_type`` is None or an empty string, it
        will be called for all messages that are otherwise unhandled.

        It should take a single argument of type :py:class:`WSMessageData`, which
        contains the data for the event.

        :param msg_type: The message type to listen to, one of the constants in 
                         this class starting with ``MSG_TYPE_`` or 
                         :py:attr:`RyverWS.MSG_TYPE_ALL` to receive all otherwise
                         unhandled messages.
        """
        if msg_type is None:
            msg_type = ""

        def _on_msg_type_inner(func: typing.Callable[[WSMessageData], typing.Awaitable]):
            self._on_msg_type[msg_type] = func
            return func
        return _on_msg_type_inner

    async def send_chat(self, to_chat: typing.Union[Chat, str], msg: str):
        """
        Send a chat message to a chat.

        :param to_chat: The chat or the JID of the chat to send the message to.
        :param msg: The message contents.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        data = {
            "type": RyverWS.MSG_TYPE_CHAT,
            "to": to_chat.get_jid() if isinstance(to_chat, Chat) else to_chat,
            "text": msg
        }
        return await self._ws_send_msg(data)

    async def send_presence_change(self, presence: str):
        """
        Send a presence change message.

        The presence change is global and not restricted to a single chat.

        :param presence: The new presence, one of the ``PRESENCE_`` constants.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_PRESENCE_CHANGED,
            "presence": presence,
        })

    async def send_typing(self, to_chat: typing.Union[Chat, str]):
        """
        Send a typing indicator to a chat.

        The typing indicator automatically clears after a few seconds or when
        a message is sent. In private messages, you can also clear it with
        :py:meth:`RyverWS.send_clear_typing()` (does not work for group chats).

        If you want to maintain the typing indicator for an extended operation,
        consider using :py:meth:`RyverWS.typing()`, which returns an async context
        manager that can be used to maintain the typing indicator for as long as desired.

        :param to_chat: The chat or the JID of the chat to send the typing status to.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_USER_TYPING,
            "state": "composing",
            "to": to_chat.get_jid() if isinstance(to_chat, Chat) else to_chat
        })
    
    async def send_clear_typing(self, to_chat: typing.Union[Chat, str]):
        """
        Clear the typing indicator for a chat.

        .. warning::
           For unknown reasons, this method **only works in private messages**.

        :param to_chat: The chat or the JID of the chat to clear the typing status for.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_USER_TYPING,
            "state": "done",
            "to": to_chat.get_jid() if isinstance(to_chat, Chat) else to_chat
        })

    @doc.acontexmanager
    def typing(self, to_chat: Chat) -> RyverWSTyping:
        """
        Get an async context manager that keeps sending a typing indicator to a chat.

        Useful for wrapping long running operations to make sure the typing indicator
        is kept, like:

        .. code:: python3
           async with session.typing(chat):
               print("do something silly")
               await asyncio.sleep(4)
               await session.send_chat(chat, "done") # or do it outside the with, doesn't matter

        :param to_chat: Where to send the typing status.
        """
        return RyverWSTyping(self, to_chat)

    async def start(self):
        """
        Start the session.
        """
        url = self._ryver.get_api_url(action="User.Login(client='pyryver')")
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

        Any future operation after closing will result in a :py:exc:`ClosedError` being raised.
        """
        self._closed = True
        # Cancel all tasks
        self._ping_task_handle.cancel()
        self._rx_task_handle.cancel()
        await self._ws.close()
        # Terminate any messages waiting for acks with an exception
        for future in self._msg_ack_table.values():
            future.set_exception(ClosedError("Connection closed"))
        # Wait until tasks terminate
        await asyncio.gather(self._ping_task_handle, self._rx_task_handle)

    async def run_forever(self):
        """
        Run forever, or until the connection is closed explicitly.

        .. note::
           By default, when the connection is lost, the session will *not* be
           automatically closed. As a result, if no action is taken, this coroutine will
           *not* exit on a connection loss. :py:meth:`RyverWS.close()` needs to be called
           explicitly to make this coroutine return. 

           You should use the :py:meth:`RyverWS.on_connection_loss()` decorator if you want
           to automatically close the connection and return on connection loss. See its
           documentation for an example.
        """
        await asyncio.gather(self._ping_task_handle, self._rx_task_handle)

    @staticmethod
    def _create_id():
        """
        Create a random message ID.

        :return: The random message ID.
        """
        return "".join(random.choice(RyverWS._VALID_ID_CHARS) for x in range(9))


from .ryver import * # nopep8

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


class WSConnectionError(Exception):
    """
    An exception raised by the real-time websockets session to indicate some kind of
    connection issue.
    """


class ClosedError(WSConnectionError):
    """
    An exception raised to indicate that the session has been closed.
    """


class ConnectionLossError(WSConnectionError):
    """
    An exception raised to indicate that the connection was lost in the middle of an
    operation.
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

    def start(self) -> None:
        """
        Start sending the typing indicator.
        """
        self._typing_task_handle = asyncio.ensure_future(self._typing_task())

    async def stop(self) -> None:
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

    :param ryver: The :py:class:`Ryver` object this live session came from.
    :param auto_reconnect: Whether to automatically reconnect on a connection loss.
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

    def __init__(self, ryver: "Ryver", auto_reconnect: bool = False):
        self._ryver = ryver
        self._ws = None
        self._msg_ack_table = {}

        self._rx_task_handle = None
        self._ping_task_handle = None

        self._on_connection_loss = None
        self._on_reconnect = None
        self._on_msg_type = {}
        self._on_event = {}

        self._auto_reconnect = auto_reconnect
        self._done = asyncio.get_event_loop().create_future()

        self._closed = True
    
    def __repr__(self) -> str:
        return f"pyryver.RyverWS(ryver={repr(self._ryver)})"

    async def __aenter__(self) -> "RyverWS":
        await self.start()
        return self

    async def __aexit__(self, exc, *exc_info):
        if not self._closed:
            await self.close()

    def get_ryver(self) -> "Ryver":
        """
        Get the Ryver session this live session was created from.

        :return: The Ryver session this live session was created from.
        """
        return self._ryver
    
    def is_connected(self) -> bool:
        """
        Get whether the websocket connection has been established.

        :return: True if connected, False otherwise.
        """
        return not self._closed
    
    def set_auto_reconnect(self, auto_reconnect: bool) -> None:
        """
        Set whether the live session should attempt to auto-reconnect on connection loss.

        :param auto_reconnect: Whether to automatically reconnect.
        """
        self._auto_reconnect = auto_reconnect

    async def _ws_send_msg(self, msg: typing.Dict[str, typing.Any], timeout: float = 5.0) -> None:
        """
        Send a message through the websocket.

        An auto-generated message ID will be attached to the message to wait for acks.

        :param msg: The raw message data.
        :param timeout: The timeout for waiting for an ack. If None, waits forever. By
                        default waits for 5s.
        :raises asyncio.TimeoutError: On ack timeout.
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
                        sys.stderr.write(f"Error: Received unexpected aiohttp specific type for WS message: {raw_msg.type}.\n")
                        if self.is_connected():
                            # Connection lost!
                            for key, future in self._msg_ack_table.items():
                                future.set_exception(ConnectionLossError(f"Connection lost while performing operation {key[1]}"))
                            self._msg_ack_table.clear()
                            if self._on_connection_loss is not None:
                                asyncio.ensure_future(self._on_connection_loss())
                            if self._auto_reconnect:
                                await self.close(cancel_rx=False)
                                while not self.is_connected():
                                    await asyncio.sleep(5.0)
                                    await self.try_reconnect()
                                if self._on_reconnect is not None:
                                    asyncio.ensure_future(self._on_reconnect())
                        if not self._auto_reconnect:
                            # Has to be done inside a task as terminate() potentially calls close()
                            # which in turn waits for _rx_task to finish, creating a deadlock
                            asyncio.ensure_future(self.terminate())
                        # Block to force a context switch
                        await asyncio.sleep(0.1)
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
                            sys.stderr.write(f"Warning: Received ack for a message not in table: {key}\n")
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
                    if self.is_connected():
                        # Connection lost!
                        for key, future in self._msg_ack_table.items():
                            future.set_exception(ConnectionLossError(f"Connection lost while performing operation {key[1]}"))
                        self._msg_ack_table.clear()
                        if self._on_connection_loss is not None:
                            asyncio.ensure_future(self._on_connection_loss())
                        # Auto reconnect
                        if self._auto_reconnect:
                            await self.close(cancel_ping=False)
                            while not self.is_connected():
                                await asyncio.sleep(5.0)
                                await self.try_reconnect()
                            if self._on_reconnect is not None:
                                asyncio.ensure_future(self._on_reconnect())
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

        If auto-reconnect is enabled, no action needs to be taken. Otherwise,
        applications are suggested to clean up and terminate, or try to reconnect using
        :py:meth:`RyverWS.try_reconnect()`. If :py:meth:`RyverWS.run_forever()` is used,
        :py:meth:`RyverWS.terminate()` should be called to make it return, unless you
        wish to reconnect.

        A simple but typical implementation is shown below for applications that do not
        wish to recover:

        .. code-block:: python

           async with ryver.get_live_session() as session:
               @session.on_connection_loss
               async def on_connection_loss():
                   await session.terminate()
        """
        self._on_connection_loss = func
        return func
    
    def on_reconnect(self, func: typing.Callable[[], typing.Awaitable]):
        """
        Decorate a coroutine to be run when auto-reconnect succeeds.

        This coroutine will be started as a task when auto-reconnect is successful. It
        should take no arguments. If auto-reconnect is not enabled, this coroutine will
        never be started.
        """
        self._on_reconnect = func
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

    async def send_chat(self, to_chat: typing.Union[Chat, str], msg: str, timeout: float = 5.0) -> None:
        """
        Send a chat message to a chat.

        :param to_chat: The chat or the JID of the chat to send the message to.
        :param msg: The message contents.
        :param timeout: The timeout for waiting for an ack. If None, waits forever. By
                        default waits for 5s.
        :raises asyncio.TimeoutError: On ack timeout.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_CHAT,
            "to": to_chat.get_jid() if isinstance(to_chat, Chat) else to_chat,
            "text": msg
        }, timeout)

    async def send_presence_change(self, presence: str, timeout: float = 5.0) -> None:
        """
        Send a presence change message.

        The presence change is global and not restricted to a single chat.

        :param presence: The new presence, one of the ``PRESENCE_`` constants.
        :param timeout: The timeout for waiting for an ack. If None, waits forever. By
                        default waits for 5s.
        :raises asyncio.TimeoutError: On ack timeout.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_PRESENCE_CHANGED,
            "presence": presence,
        }, timeout)

    async def send_typing(self, to_chat: typing.Union[Chat, str], timeout: float = 5.0) -> None:
        """
        Send a typing indicator to a chat.

        The typing indicator automatically clears after a few seconds or when
        a message is sent. In private messages, you can also clear it with
        :py:meth:`RyverWS.send_clear_typing()` (does not work for group chats).

        If you want to maintain the typing indicator for an extended operation,
        consider using :py:meth:`RyverWS.typing()`, which returns an async context
        manager that can be used to maintain the typing indicator for as long as desired.

        :param to_chat: The chat or the JID of the chat to send the typing status to.
        :param timeout: The timeout for waiting for an ack. If None, waits forever. By
                        default waits for 5s.
        :raises asyncio.TimeoutError: On ack timeout.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_USER_TYPING,
            "state": "composing",
            "to": to_chat.get_jid() if isinstance(to_chat, Chat) else to_chat
        }, timeout)
    
    async def send_clear_typing(self, to_chat: typing.Union[Chat, str], timeout: float = 5.0) -> None:
        """
        Clear the typing indicator for a chat.

        .. warning::
           For unknown reasons, this method **only works in private messages**.

        :param to_chat: The chat or the JID of the chat to clear the typing status for.
        :param timeout: The timeout for waiting for an ack. If None, waits forever. By
                        default waits for 5s.
        :raises asyncio.TimeoutError: On ack timeout.
        :raises ClosedError: If connection closed or not yet opened.  
        """
        return await self._ws_send_msg({
            "type": RyverWS.MSG_TYPE_USER_TYPING,
            "state": "done",
            "to": to_chat.get_jid() if isinstance(to_chat, Chat) else to_chat
        }, timeout)

    @doc.acontexmanager
    def typing(self, to_chat: Chat) -> RyverWSTyping:
        """
        Get an async context manager that keeps sending a typing indicator to a chat.

        Useful for wrapping long running operations to make sure the typing indicator
        is kept, like:

        .. code-block:: python

           async with session.typing(chat):
               print("do something silly")
               await asyncio.sleep(4)
               await session.send_chat(chat, "done") # or do it outside the with, doesn't matter

        :param to_chat: Where to send the typing status.
        """
        return RyverWSTyping(self, to_chat)

    async def start(self, timeout: float = 5.0) -> None:
        """
        Start the session, or reconnect after a connection loss.

        .. note::
           If there is an existing connection, it will be closed.

        :param timeout: The connection timeout in seconds. If None, waits forever.
                        By default, waits for 5 seconds.
        """
        if not self._closed:
            await self.close()

        url = self._ryver.get_api_url(action="User.Login(client='pyryver')")
        async with self._ryver._session.post(url) as resp:
            login_info = (await resp.json())["d"]
        # Get the session ID for auth and the endpoint url
        session_id = login_info["sessionId"]
        chat_url = login_info["services"]["chat"]
        self._ws = await self._ryver._session.ws_connect(chat_url)

        # Start the rx task
        self._rx_task_handle = asyncio.ensure_future(self._rx_task())
        # Authorize
        try:
            self._closed = False
            await self._ws_send_msg({
                "type": "auth",
                "authorization": "Session " + session_id,
                "agent": "Ryver",
                "resource": "Contatta-" + str(int(time.time() * 1000))
            }, timeout=timeout)
        except:
            self._closed = True
            raise
        # Start the ping task
        self._ping_task_handle = asyncio.ensure_future(self._ping_task())

    async def try_reconnect(self, timeout: float = None) -> bool:
        """
        Attempt to reconnect the websocket connection after a connection loss.

        Instead of raising an exception, if the connection cannot be established, this
        method will return False instead.

        .. note::
           If there is an existing connection, it will be closed.

        :param timeout: The connection timeout. If None, waits forever.
        :return: True if reconnection was successful; False otherwise.
        """
        try:
            await self.start(timeout)
            return True
        except (aiohttp.ClientConnectionError, aiohttp.ClientResponseError, asyncio.TimeoutError):
            return False

    async def close(self, cancel_rx: bool = True, cancel_ping: bool = True) -> None:
        """
        Close the session.

        Any future operation after closing will result in a :py:exc:`ClosedError` being
        raised, unless the session is reconnected using :py:meth:`RyverWS.start()` or
        :py:meth:`RyverWS.try_reconnect()`.

        When used as an async context manager, this method does not need to be called.

        .. note::
           Since v0.4.0, this method no longer causes :py:meth:`RyverWS.run_forever()` to
           return. Use :py:meth:`RyverWS.terminate()` if you want to close the session
           and exit ``run_forever()``.

        :param cancel_rx: Whether to cancel the rx task. For internal use only.
        :param cancel_ping: Whether to cancel the ping task. For internal use only.
        """
        self._closed = True
        # Cancel tasks
        if cancel_rx:
            self._rx_task_handle.cancel()
        if cancel_ping:
            self._ping_task_handle.cancel()
        await self._ws.close()
        # Terminate any messages waiting for acks with an exception
        for future in self._msg_ack_table.values():
            future.set_exception(ClosedError("Connection closed"))
        self._msg_ack_table.clear()
        # Wait until tasks terminate
        if cancel_rx and cancel_ping:
            await asyncio.gather(self._ping_task_handle, self._rx_task_handle)
        elif cancel_rx:
            await self._rx_task_handle
        elif cancel_ping:
            await self._ping_task_handle
    
    async def terminate(self) -> None:
        """
        Close the session and cause :py:meth:`RyverWS.run_forever()` to return.

        This method will have no effect if called twice.
        """
        if not self._closed:
            await self.close()
        if not self._done.done():
            self._done.set_result(None)

    async def run_forever(self) -> None:
        """
        Run forever, or until :py:meth:`RyverWS.terminate()` is called.

        .. note::
           Since v0.4.0, this method will no longer return if :py:meth:`RyverWS.close()`
           is called. :py:meth:`RyverWS.terminate()` must be called instead, which closes
           the session if it is unclosed.

        .. note::
           By default, this method will only return if a fatal connection loss occurs and
           auto-reconnect is not enabled. If the connection loss is recoverable, this
           method will not return even if auto-reconnect is off.

           You should use the :py:meth:`RyverWS.on_connection_loss()` decorator if you want
           to automatically close the connection and return on connection loss. See its
           documentation for an example.
        """
        if not self._done.done():
            await self._done

    @staticmethod
    def _create_id() -> str:
        """
        Create a random message ID.

        :return: The random message ID.
        """
        return "".join(random.choice(RyverWS._VALID_ID_CHARS) for x in range(9))


from .ryver import * # nopep8

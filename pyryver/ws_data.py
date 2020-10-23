"""
This module contains various data types used in :py:class:`RyverWS` callbacks.

All ``@on_`` decorated coroutines are passed an instance of one of the types defined
here when they are started.
"""

import typing
from .objects import *
from .util import *


class WSMessageData:
    """
    The data for any websocket message in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar ryver: The Ryver session that the data came from.
    :ivar ws_msg_type: The type of this websocket message. This can be one of the
                       ``MSG_TYPE_`` constants in :py:class:`pyryver.ryver_ws.RyverWS`
                       (except ``MSG_TYPE_ALL``). However, do note that the constants
                       listed there do not cover all valid values of this field.
    :ivar raw_data: The raw websocket message data.
    """

    __slots__ = ("ryver", "ws_msg_type", "raw_data")
    
    ryver: "Ryver"
    ws_msg_type: str
    raw_data: typing.Dict[str, typing.Any]

    def __init__(self, ryver: "Ryver", data: dict):
        self.ryver = ryver
        self.raw_data = data
        self.ws_msg_type = data.get("type")
    
    # For (limited) backwards compatibility
    def __getitem__(self, key):
        return self.raw_data[key]


class WSChatMessageData(WSMessageData):
    """
    The data for a chat message in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar message_id: The ID of the message (a string).
    :ivar from_jid: The JID of the sender of this message.
    :ivar to_jid: The JID of the chat this message was sent to.
    :ivar text: The contents of the message.
    :ivar subtype: The subtype of the message. This will be one of the ``SUBTYPE_``
                   constants in :py:class:`ChatMessage`.
    :ivar attachment: The file attached to this message, or None if there isn't one.
    :ivar creator: The overridden message creator (see :py:class:`Creator`), or None
                   if there isn't one.
    """

    __slots__ = ("message_id", "from_jid", "to_jid", "text", "subtype", "attachment", "creator")

    message_id: str
    from_jid: str
    to_jid: str
    text: str
    subtype: str
    attachment: File
    creator: Creator

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.message_id = data.get("key")
        self.from_jid = data.get("from")
        self.to_jid = data.get("to")
        self.text = data.get("text")
        self.subtype = data.get("subtype", ChatMessage.SUBTYPE_CHAT_MESSAGE)
        if "extras" in data and "file" in data["extras"]:
            try:
                self.attachment = File(ryver, data["extras"]["file"])
            # Failsafe to make sure this never crashes even if the JSON does not contain
            # the right data
            except KeyError:
                self.attachment = None
        else:
            self.attachment = None
        if "createSource" in data:
            self.creator = Creator(data["createSource"].get("displayName"), data["createSource"].get("avatar"))
        else:
            self.creator = None


class WSChatUpdatedData(WSChatMessageData):
    """
    The data for a chat message edited in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar message_id: The ID of the message (a string).
    :ivar from_jid: The JID of the user that edited the message.
    :ivar to_jid: The JID of the chat this message was sent to.
    :ivar text: The contents of the message after the edit. Note: In very rare
                circumstances, this field is known to be ``None``.
    :ivar subtype: The subtype of the message. This will be one of the ``SUBTYPE_``
                   constants in :py:class:`ChatMessage`.
    :ivar attachment: The file attached to this message, or None if there isn't one.
    """

    __slots__ = ()


class WSChatDeletedData(WSChatMessageData):
    """
    The data for a chat message deleted in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar message_id: The ID of the message (a string).
    :ivar from_jid: The JID of the sender of this message.
    :ivar to_jid: The JID of the chat this message was sent to.
    :ivar text: The contents of the message that was deleted.
    :ivar subtype: The subtype of the message. This will be one of the ``SUBTYPE_``
                   constants in :py:class:`ChatMessage`.
    :ivar attachment: The file attached to this message, or None if there isn't one.
    """

    __slots__ = ()


class WSPresenceChangedData(WSMessageData):
    """
    The data for a presence changed in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar presence: The new presence. This will be one of the ``PRESENCE_`` constants
                    in :py:class:`RyverWS`.
    :ivar from_jid: The JID of the user that changed their presence.
    :ivar client: The client the user is using.
    :ivar timestamp: An ISO 8601 timestamp of this event. You can use
                     :py:func:`pyryver.util.iso8601_to_datetime()` to convert it into a
                     datetime.
    """

    __slots__ = ("presence", "from_jid", "client", "timestamp")

    presence: str
    from_jid: str
    client: str
    timestamp: str

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.presence = data.get("presence")
        self.from_jid = data.get("from")
        self.client = data.get("client")
        self.timestamp = data.get("received")


class WSUserTypingData(WSMessageData):
    """
    The data for a user typing in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar from_jid: The JID of the user that started typing.
    :ivar to_jid: The JID of the chat the user started typing in.
    :ivar state: The "state" of the typing. This is almost always "composing" (for
                 typing in progress), but it could also very rarely be "done", for
                 when the user has finished typing.
    """

    __slots__ = ("from_jid", "to_jid", "state")
    
    from_jid: str
    to_jid: str
    state: str

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.from_jid = data.get("from")
        self.to_jid = data.get("to")
        self.state = data.get("state")


class WSEventData(WSMessageData):
    """
    The data for an event in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar event_type: The type of this event. This can be one of the ``EVENT_``
                      constants in :py:class:`pyryver.ryver_ws.RyverWS` (except
                      ``EVENT_ALL``). However, do note that the constants listed there
                      do not cover all valid values of this field.
    :ivar event_data: The data of this event. This is a dictionary mapping strings to
                      values of any type. The format depends on the event type. The
                      format of some events are documented in the docs of the
                      ``EVENT_`` constants.
    """

    __slots__ = ("event_type", "event_data")
    
    event_type: str
    event_data: typing.Dict[str, typing.Any]

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.event_type = data.get("topic")
        self.event_data = data.get("data")


from .ryver import * # nopep8

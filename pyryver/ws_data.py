import typing
from pyryver.objects import *
from pyryver.util import *


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
    
    ryver: "Ryver"
    ws_msg_type: str
    raw_data: typing.Dict[str, typing.Any]

    def __init__(self, ryver: "Ryver", data: dict):
        self.ryver = ryver
        self.raw_data = data
        self.ws_msg_type = data["type"]


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
    """

    message_id: str
    from_jid: str
    to_jid: str
    text: str
    subtype: str
    attachment: File

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.message_id = data["key"]
        self.from_jid = data["from"]
        self.to_jid = data["to"]
        self.text = data["text"]
        self.subtype = data.get("subtype", ChatMessage.SUBTYPE_CHAT_MESSAGE)
        self.attachment = File(ryver, data["extras"]) if "extras" in data else None


class WSChatUpdatedData(WSChatMessageData):
    """
    The data for a chat message edited in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar message_id: The ID of the message (a string).
    :ivar from_jid: The JID of the user that edited the message.
    :ivar to_jid: The JID of the chat this message was sent to.
    :ivar text: The contents of the message after the edit.
    :ivar subtype: The subtype of the message. This will be one of the ``SUBTYPE_``
                   constants in :py:class:`ChatMessage`.
    :ivar attachment: The file attached to this message, or None if there isn't one.
    """


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


class WSPresenceChangedData(WSMessageData):
    """
    The data for a presence changed in :py:class:`pyryver.ryver_ws.RyverWS`.

    :ivar presence: The new presence. This will be one of the ``PRESENCE_`` constants
                    in :py:class:`RyverWS`.
    :ivar from_jid: The JID of the user that changed their presence.
    :ivar client: The client the user is using.
    :ivar timestamp: An ISO 8601 timestamp of this event. You can use
                     :py:func:`pyryver.util.iso8601_to_datetime()` to conver it into a
                     datetime.
    """

    presence: str
    from_jid: str
    client: str
    timestamp: str

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.presence = data["presence"]
        self.from_jid = data["from"]
        self.client = data["client"]
        self.timestamp = data["timestamp"]


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
    
    event_type: str
    event_data: typing.Dict[str, typing.Any]

    def __init__(self, ryver: "Ryver", data: dict):
        super().__init__(ryver, data)
        self.event_type = data["topic"]
        self.event_data = data["data"]


from pyryver.ryver import * # nopep8

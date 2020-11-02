"""
This module contains various Ryver entities and other objects.
"""


import aiohttp
import datetime
import typing
from abc import ABC, abstractmethod
from .util import *


class Creator:
    """
    A message creator, with a name and an avatar.

    This can be used to override the sender's display name and avatar.

    :param name: The overridden display name
    :param avatar: The overridden avatar (a url to an image)
    """

    __slots__ = ("name", "avatar")

    def __init__(self, name: str, avatar: str = ""):
        self.name = name
        self.avatar = avatar
    
    def __repr__(self) -> str:
        return f"pyryver.Creator(name={self.name}, avatar={self.avatar})"

    def to_dict(self) -> dict:
        """
        Convert this Creator object to a dictionary to be used in a request.

        .. warning::
           This method is intended for internal use only.

        :return: The dict representation of this object.
        """
        return {
            "displayName": self.name,
            "avatar": self.avatar
        }


class TaskTag:
    """
    A tag for tasks.

    .. note::
       This class does not inherit from :py:class:`Object`. It is a helper created to
       work with task tag definitions in chats.

       All colours are in RGBA hex.

    :param name: The tag name.
    :param text_color: The text colour.
    :param background_color: The background color.
    :param border_color: The border color.
    """

    __slots__ = ("_data",)

    def __init__(self, name: typing.Optional[str], text_color: typing.Optional[str],
                 background_color: typing.Optional[str], border_color: typing.Optional[str]):
        self._data = {
            "name": name,
            "colors": {
                "text": text_color,
                "background": background_color,
                "border": border_color,
            }
        }
    
    def __repr__(self) -> str:
        return f"pyryver.TaskTag(name={self.get_name()}, text_color={self.get_text_color()}, background_color={self.get_background_color}, border_color={self.get_border_color})"

    @classmethod
    def from_data(cls, data: dict) -> "TaskTag":
        """
        Construct a instance from raw data.

        .. warning::
           This method is intended for internal use only.

        :param data: The instance data.
        :return: The constructed instance.
        """
        inst = cls(None, None, None, None)
        inst._data = data
        return inst

    def to_dict(self) -> dict:
        """
        Convert this ``TaskTag`` object to a dictionary to be used in a request.

        .. warning::
           This method is intended for internal use only.

        :return: The dict representation of this object.
        """
        return self._data

    def get_name(self) -> str:
        """
        Get the name of this tag.

        :return: The name of the tag.
        """
        return self._data["name"]

    def get_text_color(self) -> str:
        """
        Get the text colour of this tag, as an RGBA hex colour code.

        :return: The text colour of the tag.
        """
        return self._data["colors"]["text"]

    def get_background_color(self) -> str:
        """
        Get the background colour of this tag, as an RGBA hex colour code.

        :return: The background colour of the tag.
        """
        return self._data["colors"]["background"]

    def get_border_color(self) -> str:
        """
        Get the border colour of this tag, as an RGBA hex colour code.

        :return: The border colour of the tag.
        """
        return self._data["colors"]["border"]


#: A dict that maps internal strings for object types to classes.
TYPES_DICT = {}


class Object(ABC):
    """
    Base class for all Ryver objects.

    :param ryver: The parent :py:class:`pyryver.pyryver.Ryver` instance.
    :param data: The object's data.
    """

    __slots__ = ("_ryver", "_data", "_id")

    # The _OBJ_TYPE of each class inheriting from Object is used during object creation to determine the type
    _OBJ_TYPE = "__object"

    def __init__(self, ryver: "Ryver", data: dict):
        self._ryver = ryver  # type: Ryver
        self._data = data
        self._id = data["id"]

    def __eq__(self, other) -> bool:
        return isinstance(other, Object) and other.get_id() == self.get_id()
    
    def __hash__(self) -> int:
        return self.get_id()
    
    def __repr__(self, **kwargs) -> str:
        try:
            kwargs["name"] = f"'{self.get_name()}'"
        except (AttributeError, TypeError):
            pass
        args = "".join(f", {k}={v}" for k, v in kwargs.items())
        return f"pyryver.{type(self).__name__}(id={self._id}{args})"
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register types in the dict
        TYPES_DICT[cls._OBJ_TYPE] = cls

    def get_ryver(self) -> "Ryver":
        """
        Get the Ryver session this object was retrieved from.

        :return: The Ryver session associated with this object.
        """
        return self._ryver

    def get_id(self) -> typing.Union[int, str]:
        """
        Get the ID of this object.

        For a :py:class:`ChatMessage` this is a string. For all other types, it is
        an int.

        :return: The ID of this object.
        """
        return self._id

    def get_entity_type(self) -> str:
        """
        Get the entity type of this object.

        :return: The entity type of this object, or if no entity of such type exists, ``<unknown>``.
        """
        return ENTITY_TYPES.get(self.get_type(), "<unknown>")

    def get_raw_data(self) -> dict:
        """
        Get the raw data of this object.

        The raw data is a dictionary directly obtained from parsing the JSON
        response.

        :return: The raw data of this object.
        """
        return self._data

    def get_api_url(self, *args, **kwargs) -> str:
        """
        Uses :py:meth:`Ryver.get_api_url()` to get a URL for working with the Ryver API.

        .. warning::
           This method is intended for internal use only.

        This is equivalent to calling :py:meth:`Ryver.get_api_url()`, but with the first
        two parameters set to ``self.get_type()`` and ``self.get_id()``.

        :return: The formatted URL for performing requests.
        """
        return self._ryver.get_api_url(self.get_type(), self.get_id(), *args, **kwargs)

    def get_create_date(self) -> typing.Optional[str]:
        """
        Get the date this object was created as an ISO 8601 timestamp.

        .. note::
           This method does not work for all objects. For some objects, it will return
           None.

        .. tip::
           You can use :py:meth:`pyryver.util.iso8601_to_datetime()` to convert the 
           timestamps returned by this method into a datetime.

        :return: The creation date of this object, or None if not supported.
        """
        return self._data.get("createDate", None)

    def get_modify_date(self) -> typing.Optional[str]:
        """
        Get the date this object was last modified as an ISO 8601 timestamp.

        .. note::
           This method does not work for all objects. For some objects, it will return
           None.

        .. tip::
           You can use :py:meth:`pyryver.util.iso8601_to_datetime()` to convert the 
           timestamps returned by this method into a datetime.

        :return: The modification date of this object, or None if not supported.
        """
        return self._data.get("modifyDate", None)
    
    def get_app_link(self) -> str:
        """
        Get a link to this object that opens the app to this object.

        .. note::
           This method does not work for some types such as messages and topic/task
           replies. Additionally, only types with :py:meth:`Object.is_instantiable()`
           true can be linked to. Calling this method on an object of an invalid type
           will result in a ``TypeError``.

        :raises TypeError: If this object cannot be linked to.
        :return: The in-app link for this object.
        """
        if not self.is_instantiable():
            raise TypeError(f"The type {self.__class__.__name__} is not instantiable!")
        return f"https://{self._ryver.org}.ryver.com/#{self.get_type()}/{self.get_id()}"
    
    def get_creator(self) -> typing.Optional[Creator]:
        """
        Get the Creator of this object.

        Note that this is different from the author. Creators are used to
        override the display name and avatar of a user. If the username and 
        avatar were not overridden, this will return None.

        Not all objects support this operation. If not supported, this will return
        ``None``.

        :return: The overridden creator of this message.
        """
        if "createSource" in self._data and self._data["createSource"] is not None:
            return Creator(self._data["createSource"]["displayName"], self._data["createSource"]["avatar"])
        else:
            return None

    async def get_deferred_field(self, field: str, field_type: str) -> typing.Union[typing.Type["Object"], typing.List[typing.Type["Object"]]]:
        """
        Get the value of a field of this object that exists, but is not included
        ("__deferred" in the Ryver API).

        .. warning::
           This function is intended for internal use only.

        This function will automatically infer from the result's contents whether
        to return a single object or a list of objects.

        If the field cannot be retrieved, a ``ValueError`` will be raised.

        :param field: The name of the field.
        :param field_type: The type of the field, must be a ``TYPE_`` constant.
        :return: The expanded value of this field as an object or a list of objects.
        :raises ValueError: When the field cannot be expanded.
        """
        constructor = TYPES_DICT[field_type]
        # First check if the field is present
        if field in self._data and "__deferred" not in self._data[field]:
            if "results" in self._data[field]:
                return [constructor(self._ryver, obj_data) for obj_data in self._data[field]["results"]]
            else:
                return constructor(self._ryver, self._data[field])
        url = self.get_api_url(expand=field, select=field)
        async with self._ryver._session.get(url) as resp:
            data = (await resp.json())["d"]["results"][field]
        if "__deferred" in data:
            raise ValueError(
                "Cannot obtain field! The field cannot be expanded for some reason.")
        self._data[field] = data
        # Check if the result should be a list
        if "results" in data:
            return [constructor(self._ryver, obj_data) for obj_data in data["results"]]
        else:
            return constructor(self._ryver, data)

    async def get_create_user(self) -> typing.Optional["User"]:
        """
        Get the user that created this object.

        .. note::
           This method does not work for all objects. If not supported, it will return
           None.

        :return: The user that created this object, or None if not supported.
        """
        if "createUser" in self._data:
            try:
                return await self.get_deferred_field("createUser", TYPE_USER)
            except ValueError:
                return None
        else:
            return None

    async def get_modify_user(self) -> typing.Optional["User"]:
        """
        Get the user that modified this object.

        .. note::
           This method does not work for all objects. If not supported, it will return
           None.

        :return: The user that last modified this object, or None if not supported.
        """
        if "modifyUser" in self._data:
            try:
                return await self.get_deferred_field("modifyUser", TYPE_USER)
            except ValueError:
                return None
        else:
            return None

    @classmethod
    def get_type(cls) -> str:
        """
        Get the type of this object.

        :return: The type of this object.
        """
        return cls._OBJ_TYPE
    
    @classmethod
    def is_instantiable(cls) -> bool:
        """
        Get whether this object type is instantiable.

        Some types of objects cannot be instantiated, as they are actually not a part
        of the REST API, such as :py:class:`Message`, :py:class:`Chat`, and other
        abstract types. If the type can be instantiated, this class method will return
        ``True``.

        Note that even though a type may not be instantiable, its derived types could
        still be. For example, :py:class:`Chat` is not instantiable, but one of its
        derived types, :py:class:`User`, is instantiable.

        :return: Whether this type is instantiable.
        """
        return not cls.get_type().startswith("__")

    @classmethod
    async def get_by_id(cls, ryver: "Ryver", obj_id: int) -> typing.Type["Object"]:
        """
        Retrieve an object of this type by ID.
        
        :param ryver: The Ryver session to retrieve the object from.
        :param obj_id: The ID of the object to retrieve.
        :raises TypeError: If this type is not instantiable.
        :return: The object requested.
        """
        if not cls.is_instantiable():
            raise TypeError(f"The type {cls.__name__} is not instantiable!")
        return await ryver.get_object(cls.get_type(), obj_id)


class Message(Object):
    """
    Any generic Ryver message, with an author, body, and reactions.
    """

    __slots__ = ()

    _OBJ_TYPE = "__message"

    def __repr__(self, **kwargs) -> str:
        body = self.get_body()
        body = body if len(body) < 100 else body[:100] + "..."
        return super().__repr__(body=repr(body), **kwargs)

    def get_body(self) -> str:
        """
        Get the body of this message.

        Note that this may be None in some circumstances.

        :return: The body of this message.
        """
        return self._data["body"]

    async def get_author(self) -> "User":
        """
        Get the author of this message, as a :py:class:`User` object.

        :return: The author of this message.
        """
        return await self.get_create_user()

    async def react(self, emoji: str) -> None:
        """
        React to this message with an emoji. 

        .. note::
           This method does **not** update the reactions property of this object.

        :param emoji: The string name of the reaction (e.g. "thumbsup").
        """
        url = self.get_api_url(action=f"React(reaction='{emoji}')")
        await self._ryver._session.post(url)

    async def unreact(self, emoji: str) -> None:
        """
        Unreact with an emoji.

        .. note::
           This method does **not** update the reactions property of this object.

        :param emoji: The string name of the reaction (e.g. "thumbsup").
        """
        url = self.get_api_url(action=f"UnReact(reaction='{emoji}')")
        await self._ryver._session.post(url)

    def get_reactions(self) -> dict:
        """
        Get the reactions on this message.

        Returns a dict of ``{emoji: [users]}``.

        :return: A dict matching each emoji to the users that reacted with that emoji.
        """
        return self._data['__reactions']

    def get_reaction_counts(self) -> dict:
        """
        Count the number of reactions for each emoji on a message.

        Returns a dict of ``{emoji: number_of_reacts}``.

        :return: A dict matching each emoji to the number of users that reacted with that emoji.
        """
        reactions = self.get_reactions()
        counts = {reaction: len(users)
                  for reaction, users in reactions.items()}
        return counts

    async def delete(self) -> None:
        """
        Delete this message.
        """
        await self._ryver._session.delete(self.get_api_url(format="json"))


class PostedMessage(Message):
    """
    A topic, task, topic reply, etc.
    """

    __slots__ = ()

    _OBJ_TYPE = "__postedMessage"

    async def get_attachments(self) -> typing.List["Storage"]:
        """
        Get all the attachments of this message.

        As the attachments could be files, links or otherwise, :py:class:`Storage`
        objects are returned instead of :py:class:`File` objects.

        :return: A list of attachments of this message.
        """
        url = self.get_api_url(
            expand="attachments,attachments/storage", select="attachments")
        async with self._ryver._session.get(url) as resp:
            attachments = (await resp.json())["d"]["results"]["attachments"]["results"]
        results = []
        for attachment in attachments:
            # Check the type
            if attachment["recordType"] == Storage.STORAGE_TYPE_FILE:
                # Make it so that the file can be retrieved
                attachment["storage"]["file"] = attachment
                results.append(Storage(self._ryver, attachment["storage"]))
            else:
                results.append(Storage(self._ryver, attachment))
        return results


class PostedComment(PostedMessage):
    """
    A topic reply or task comment.
    """

    __slots__ = ()

    _OBJ_TYPE = "__comment"

    # Override as a different field is used
    def get_body(self) -> str:
        """
        Get the body of this comment/reply.

        :return: The body of this comment/reply.
        """
        return self._data["comment"]
    
    async def edit(self, message: typing.Optional[str] = NO_CHANGE, creator: typing.Optional[Creator] = NO_CHANGE,
                   attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = NO_CHANGE) -> None:
        """
        Edit this comment/reply.

        .. note::
           You can only edit a comment/reply if it was sent by you (even if you are an
           admin). Attempting to edit another user's comment/reply will result in a 
           :py:exc:`aiohttp.ClientResponseError`.

           The file attachments (if specified) will **replace** all existing attachments.

           Additionally, this method also updates these properties in this object.

        If any parameters are unspecified or :py:const:`NO_CHANGE`, they will be left
        as-is. Passing ``None`` for parameters for which ``None`` is not a valid value
        will also result in the value being unchanged.

        :param message: The contents of the comment/reply (optional).
        :param creator: The overridden creator (optional).
        :param attachments: A number of attachments for this comment/reply (optional).
        """
        url = self.get_api_url(format="json")
        data = {}
        if message is not NO_CHANGE and message is not None:
            data["comment"] = message
        if creator is not NO_CHANGE:
            data["createSource"] = creator.to_dict() if creator is not None else None
        if attachments is not NO_CHANGE and attachments is not None:
            data["attachments"] = {
                "results": [attachment.get_file().get_raw_data() if isinstance(attachment, Storage) 
                            and attachment.get_storage_type() == Storage.STORAGE_TYPE_FILE 
                            else attachment.get_raw_data() for attachment in attachments]
            }
        await self._ryver._session.patch(url, json=data)
        self._data.update(data)


class TopicReply(PostedComment):
    """
    A reply on a topic.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TOPIC_REPLY

    async def get_topic(self) -> "Topic":
        """
        Get the topic this reply was sent to.

        :return: The topic associated with this reply.
        """
        return await self.get_deferred_field("post", TYPE_TOPIC)


class Topic(PostedMessage):
    """
    A Ryver topic in a chat.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TOPIC

    def get_subject(self) -> str:
        """
        Get the subject of this topic.

        :return: The subject of this topic.
        """
        return self._data["subject"]

    def is_stickied(self) -> bool:
        """
        Return whether this topic is stickied (pinned) to the top of the list.

        :return: Whether this topic is stickied.
        """
        return self._data["stickied"]

    def is_archived(self) -> bool:
        """
        Return whether this topic is archived.

        :return: Whether this topic is archived.
        """
        return self._data["archived"]

    async def archive(self, archived: bool = True) -> None:
        """
        Archive or un-archive this topic.

        :param archived: Whether the topic should be archived.
        """
        url = self.get_api_url(format="json")
        data = {
            "archived": archived
        }
        await self._ryver._session.patch(url, json=data)
    
    async def unarchive(self) -> None:
        """
        Un-archive this topic.

        This is the same as calling :py:meth:`Topic.archive()` with False.
        """
        await self.archive(False)

    async def reply(self, message: str, creator: typing.Optional[Creator] = None,
                    attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = None) -> TopicReply:
        """
        Reply to the topic.

        .. note::
           For unknown reasons, overriding the creator does not seem to work for this method.

        .. tip::
           To attach files to the reply, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the files you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for link attachments.

        :param message: The reply content
        :param creator: The overridden creator (optional). **Does not work.**
        :param attachments: A number of attachments for this reply (optional).
        :return: The created reply.
        """
        url = self._ryver.get_api_url(TYPE_TOPIC_REPLY, format="json")
        data = {
            "comment": message,
            "post": {
                "id": self.get_id()
            }
        }
        if creator is not None:
            data["createSource"] = creator.to_dict()
        if attachments:
            data["attachments"] = {
                "results": [attachment.get_file().get_raw_data() if isinstance(attachment, Storage) 
                            and attachment.get_storage_type() == Storage.STORAGE_TYPE_FILE 
                            else attachment.get_raw_data() for attachment in attachments]
            }
        async with self._ryver._session.post(url, json=data) as resp:
            return TopicReply(self._ryver, (await resp.json())["d"]["results"])

    async def get_replies(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator[TopicReply]:
        """
        Get all the replies to this topic.

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results (optional).
        :return: An async iterator for the replies of this topic.
        """
        url = self.get_api_url(action="comments", format="json")
        async for reply in self._ryver.get_all(url=url, top=top, skip=skip):
            yield TopicReply(self._ryver, reply) #NOSONAR

    async def edit(self, subject: typing.Optional[str] = NO_CHANGE, body: typing.Optional[str] = NO_CHANGE,
                   stickied: typing.Optional[bool] = NO_CHANGE, creator: typing.Optional[Creator] = NO_CHANGE,
                   attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = NO_CHANGE) -> None:
        """
        Edit this topic.

        .. note::
           Unlike editing topic replies and chat messages, admins have permission to
           edit any topic regardless of whether they created it.

           The file attachments (if specified) will **replace** all existing attachments.

           Additionally, this method also updates these properties in this object.

        If any parameters are unspecified or :py:const:`NO_CHANGE`, they will be left
        as-is. Passing ``None`` for parameters for which ``None`` is not a valid value
        will also result in the value being unchanged.

        :param subject: The subject (or title) of the topic (optional).
        :param body: The contents of the topic (optional).
        :param stickied: Whether to sticky (pin) this topic to the top of the list (optional).
        :param creator: The overridden creator (optional).
        :param attachments: A number of attachments for this topic (optional).
        """
        url = self.get_api_url(format="json")
        data = {}
        if subject is not NO_CHANGE and subject is not None:
            data["subject"] = subject
        if body is not NO_CHANGE and body is not None:
            data["body"] = body
        if stickied is not NO_CHANGE and stickied is not None:
            data["stickied"] = stickied
        if creator is not NO_CHANGE:
            data["createSource"] = creator.to_dict() if creator is not None else None
        if attachments is not NO_CHANGE and attachments is not None:
            data["attachments"] = {
                "results": [attachment.get_file().get_raw_data() if isinstance(attachment, Storage) 
                            and attachment.get_storage_type() == Storage.STORAGE_TYPE_FILE 
                            else attachment.get_raw_data() for attachment in attachments]
            }
        await self._ryver._session.patch(url, json=data)
        self._data.update(data)


class ChatMessage(Message):
    """
    A message that was sent to a chat.

    .. note::
       Chat message are actually not a part of the Ryver REST APIs, since they aren't
       standalone objects (a chat is required to obtain one). As a result, they are a
       bit different from the other objects. Their IDs are strings rather than ints,
       and they are not instantiable (and therefore cannot be obtained from
       :py:meth:`Ryver.get_object()` or :py:meth:`Object.get_by_id()`.)

    :cvar MSG_TYPE_PRIVATE: A private message between users.
    :cvar MSG_TYPE_GROUPCHAT: A message sent to a group chat (team or forum).

    :cvar SUBTYPE_CHAT_MESSAGE: A regular chat message sent by a user.
    :cvar SUBTYPE_TOPIC_ANNOUNCEMENT: An automatic chat message that announces the creation of a new topic.
    :cvar SUBTYPE_TASK_ANNOUNCEMENT: An automatic chat message that announces the creation of a new task.
    """

    __slots__ = ()

    _OBJ_TYPE = "__chatMessage"

    MSG_TYPE_PRIVATE = "chat"
    MSG_TYPE_GROUPCHAT = "groupchat"

    # Note: CHAT_MESSAGE is not a real subtype in the REST API, and is instead
    # represented as no subtype. It is here only for completeness.
    SUBTYPE_CHAT_MESSAGE = "chat"
    SUBTYPE_TOPIC_ANNOUNCEMENT = "topic_share"
    SUBTYPE_TASK_ANNOUNCEMENT = "task_share"

    def __repr__(self, **kwargs) -> str:
        return super().__repr__(chat_id=self.get_chat_id(), **kwargs)

    def get_msg_type(self) -> str:
        """
        Get the type of this message (private message or group chat message).

        The returned value will be one of the ``MSG_TYPE_`` constants in this class.

        :return: The type of this message.
        """
        return self._data["messageType"]
    
    def get_subtype(self) -> str:
        """
        Get the subtype of this message (regular message or topic/task announcement).

        The returned value will be one of the ``SUBTYPE_`` constants in this class.

        :return: The subtype of this message.
        """
        return self._data.get("subtype", ChatMessage.SUBTYPE_CHAT_MESSAGE)

    def get_time(self) -> str:
        """
        Get the time this message was sent, as an ISO 8601 timestamp.

        .. tip::
           You can use :py:meth:`pyryver.util.iso8601_to_datetime()` to convert the 
           timestamps returned by this method into a datetime.

        :return: The time this message was sent, as an ISO 8601 timestamp.
        """
        return self._data["when"]

    def get_author_id(self) -> int:
        """
        Get the ID of the author of this message.

        :return: The author ID of the message.
        """
        return self._data["from"]["id"]

    def get_chat_type(self) -> str:
        """
        Gets the type of chat that this message was sent to, as a string.

        :return: The type of the chat this message was sent to.
        """
        return get_type_from_entity(self._data["to"]["__metadata"]["type"])

    def get_chat_id(self) -> int:
        """
        Get the id of the chat that this message was sent to, as an integer.

        Note that this is different from :py:meth:`get_chat()` as the id is stored in
        the message data and is good for most API purposes while ``get_chat()``
        returns an entire Chat object, which might not be necessary depending
        on what you're trying to do.

        :return: The ID of the chat this message was sent to.
        """
        return self._data["to"]["id"]

    def get_attached_file(self) -> typing.Optional["File"]:
        """
        Get the file attached to this message, if there is one.

        .. note::
           Files obtained from this only have a limited amount of information,
           including the ID, name, URL, size and type. Attempting to get any other info
           will result in a KeyError. To obtain the full file info, use :py:meth:`Ryver.get_object()`
           with `TYPE_FILE <pyryver.util.TYPE_FILE>` and the ID.

        .. note::
           Even if the attachment was a link and not a file, it will still be returned
           as a ``File`` object, as there seems to be no way of telling the type of the
           attachment just from the info provided in the message object.

        Returns None otherwise.

        :return: The attached file or link.
        """
        if "extras" in self._data and "file" in self._data["extras"]:
            return File(self._ryver, self._data["extras"]["file"])
        else:
            return None
    
    def get_announced_topic_id(self) -> typing.Optional[int]:
        """
        Get the ID of the topic this message is announcing.

        This is only a valid operation for messages that announce a new topic.
        In other words, :py:meth:`ChatMessage.get_subtype()` must return
        :py:attr:`ChatMessage.SUBTYPE_TOPIC_ANNOUNCEMENT`. If this message does not
        announce a topic, this method will return ``None``.

        :return: The ID of the topic that is announced by this message, or ``None``.
        """
        if "post" in self._data:
            return self._data["post"]["id"]
        else:
            return None
    
    def get_announced_task_id(self) -> typing.Optional[int]:
        """
        Get the ID of the task this message is announcing.

        This is only a valid operation for messages that announce a new task.
        In other words, :py:meth:`ChatMessage.get_subtype()` must return
        :py:attr:`ChatMessage.SUBTYPE_TASK_ANNOUNCEMENT`. If this message does not
        announce a topic, this method will return ``None``.

        :return: The ID of the task that is announced by this message, or ``None``.
        """
        if "task" in self._data:
            return self._data["task"]["id"]
        else:
            return None

    async def get_author(self) -> "User":
        """
        Get the author of this message, as a :py:class:`User` object.

        .. tip::
           For chat messages, you can get the author ID without sending any requests,
           with :py:meth:`ChatMessage.get_author_id()`.

        :return: The author of this message.
        """
        return await self._ryver.get_object(TYPE_USER, self.get_author_id())

    async def get_chat(self) -> "Chat":
        """
        Get the chat that this message was sent to, as a :py:class:`Chat` object.

        :return: The chat this message was sent to.
        """
        return await self._ryver.get_object(self.get_chat_type(), self.get_chat_id())

    # Override Message.react() because a different URL is used
    async def react(self, emoji: str) -> None:
        """
        React to this task with an emoji. 

        .. note::
           This method does **not** update the reactions property of this object.

        :param emoji: The string name of the reaction (e.g. "thumbsup").
        """
        url = self._ryver.get_api_url(self.get_chat_type(
        ), self.get_chat_id(), "Chat.React()", format="json")
        data = {
            "id": self.get_id(),
            "reaction": emoji
        }
        await self._ryver._session.post(url, json=data)

    # Override Message.unreact() because a different URL is used
    async def unreact(self, emoji: str) -> None:
        """
        Unreact with an emoji.

        .. note::
           This method does **not** update the reactions property of this object.

        :param emoji: The string name of the reaction (e.g. "thumbsup").
        """
        url = self._ryver.get_api_url(self.get_chat_type(
        ), self.get_chat_id(), "Chat.UnReact()", format="json")
        data = {
            "id": self.get_id(),
            "reaction": emoji
        }
        await self._ryver._session.post(url, json=data)

    async def delete(self) -> None:
        """
        Deletes the message.
        """
        url = self._ryver.get_api_url(self.get_chat_type(
        ), self.get_chat_id(), "Chat.DeleteMessage()", format="json")
        data = {
            "id": self.get_id(),
        }
        await self._ryver._session.post(url, json=data)

    async def edit(self, message: typing.Optional[str] = NO_CHANGE, creator: typing.Optional[Creator] = NO_CHANGE, 
                   attachment: typing.Optional[typing.Union["Storage", "File"]] = NO_CHANGE, from_user: typing.Optional["User"] = None) -> None:
        """
        Edit this message.

        .. note::
           You can only edit a message if it was sent by you (even if you are an
           admin). Attempting to edit another user's message will result in a 
           :py:exc:`aiohttp.ClientResponseError`.

           This also updates these properties in this object.

        .. tip::
           To attach a file to the message, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the file you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for a link attachment.

        .. warning::
           ``from_user`` **must** be set when using attachments with private messages.
           Otherwise, a ``ValueError`` will be raised. It should be set to the user that
           is sending the message (the user currently logged in).

           It is not required to be set if the message is being sent to a forum/team.
        
        If any parameters are unspecified or :py:const:`NO_CHANGE`, they will be left
        as-is. Passing ``None`` for parameters for which ``None`` is not a valid value
        will also result in the value being unchanged.

        :param message: The new message contents (optional).
        :param creator: The new creator (optional).
        :param attachment: An attachment for this message, e.g. a file or a link (optional). Can be either a ``Storage`` or a ``File`` object.
        :param from_user: The user that is sending this message (the user currently logged in); **must** be set when using attachments in private messages (optional).
        :raises ValueError: If a ``from_user`` is not provided for a private message attachment.
        """
        url = self._ryver.get_api_url(
            self.get_chat_type(), self.get_chat_id(), "Chat.UpdateMessage()", format="json")
        data = {
            "id": self.get_id(),
        }
        if message is not NO_CHANGE and message is not None:
            data["body"] = message
        if creator is not NO_CHANGE:
            data["createSource"] = creator.to_dict() if creator is not None else None
        if attachment is not NO_CHANGE:
            # Clear attachment
            if attachment is None:
                data["embeds"] = {}
            else:
                chat = await self.get_chat()
                data.update(await chat._process_attachment(message, attachment, from_user))
        await self._ryver._session.post(url, json=data)
        self._data.update(data)


class Chat(Object):
    """
    Any Ryver chat you can send messages to.

    E.g. Teams, forums, user DMs, etc.
    """

    __slots__ = ()

    _OBJ_TYPE = "__chat"

    def get_jid(self) -> str:
        """
        Get the JID (JabberID) of this chat.

        The JID is used in the websockets interface.

        :return: The JID of this chat.
        """
        return self._data["jid"]

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this chat.

        :return: The name of this chat.
        """

    def get_task_tags(self) -> typing.List[TaskTag]:
        """
        Get a list of task tags defined in this chat, as ``TaskTag`` objects.

        :return: The defined task tags of this chat.
        """
        return [TaskTag.from_data(data) for data in self._data["tagDefs"]]

    async def set_task_tags(self, tags: typing.Iterable[TaskTag]):
        """
        Set the task tags defined in this chat.

        .. note::
           This will erase any existing tags.

           This method also updates the task tags property of this object.

        :param tags: The new tags as a list of ``TaskTag``s.
        """
        data = {
            "tagDefs": [tag.to_dict() for tag in tags]
        }
        url = self.get_api_url()
        await self._ryver._session.patch(url, json=data)
        self._data["tagDefs"] = data["tagDefs"]
    
    async def _process_attachment(self, message: str, attachment: typing.Union["Storage", "File"],
                                  from_user: "User" = None) -> typing.Dict[str, typing.Any]:
        """
        Process a ``Storage`` object for attaching to a chat message.

        .. warning::
           This method is intended for internal use only.
        
        :param message: The chat message.
        :param attachment: The attachment to process. Can be either a ``Storage`` or a ``File`` object.
        :param from_user: The user that is sending this message (the user currently logged in); **must** be set when using attachments in private messages (optional).
        :raises ValueError: If a ``from_user`` is not provided for a private message attachment.
        :return: The data that can be used to send this message attachment.
        """
        if from_user is None and isinstance(self, User):
            raise ValueError("Message attachments in private messages require from_user to be set!")
        # The Ryver API is weird
        out_assoc = {
            "results": [
                {
                    "inId": self.get_id(),
                    "inSecured": True,
                    "inType": self.get_entity_type(),
                    "inName": self.get_name(),
                }
            ]
        }
        if isinstance(self, User):
            out_assoc["results"].insert(0, {
                "inId": from_user.get_id(),
                "inSecured": True,
                "inType": from_user.get_entity_type(),
                "inName": from_user.get_name(),
            })
        # Extract some values to be used later
        if isinstance(attachment, File):
            content_id = attachment.get_id()
            content_url = attachment.get_url()
            content_mime = attachment.get_MIME_type()
        else:
            content_id = attachment.get_content_id()
            content_url = attachment.get_content_url()
            content_mime = attachment.get_content_MIME_type()

        # PATCH to update the outAssociations of the file
        patch_url = self._ryver.get_api_url(TYPE_FILE, content_id, format="json")
        await self._ryver._session.patch(patch_url, json={
            "outAssociations": out_assoc
        })
        # Now GET to get the embeds
        embeds_url = self._ryver.get_api_url(TYPE_FILE, content_id, select="embeds")
        async with self._ryver._session.get(embeds_url) as resp:
            embeds = await resp.json()
        data = {
            "extras": {
                "file": {
                    "fileName": attachment.get_name(),
                    "fileSize": attachment.get_size(),
                    "id": content_id,
                    "outAssociations": out_assoc,
                    "url": content_url,
                    "fileType": content_mime,
                    "chatBody": message
                }
            },
            "embeds": embeds["d"]["results"]["embeds"],
            "body": message + f"\n\n[{attachment.get_name()}]({content_url})"
        }
        return data

    async def send_message(self, message: str, creator: typing.Optional[Creator] = None,
                           attachment: typing.Optional[typing.Union["Storage", "File"]] = None,
                           from_user: typing.Optional["User"] = None) -> str:
        """
        Send a message to this chat.

        Specify a creator to override the username and profile of the message creator.

        .. tip::
           To attach a file to the message, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the file you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for a link attachment.

        .. warning::
           ``from_user`` **must** be set when using attachments with private messages.
           Otherwise, a ``ValueError`` will be raised. It should be set to the user that
           is sending the message (the user currently logged in).

           It is not required to be set if the message is being sent to a forum/team.

        Returns the ID of the chat message sent (**not** the message object itself). 
        Note that message IDs are strings.

        :param message: The message contents.
        :param creator: The overridden creator; optional, if unset uses the logged-in user's profile.
        :param attachment: An attachment for this message, e.g. a file or a link (optional). Can be either a ``Storage`` or a ``File`` object.
        :param from_user: The user that is sending this message (the user currently logged in); **must** be set when using attachments in private messages (optional).
        :raises ValueError: If a ``from_user`` is not provided for a private message attachment.
        :return: The ID of the chat message that was sent.
        """
        url = self.get_api_url("Chat.PostMessage()", format="json")
        data = {
            "body": message
        }
        if creator is not None:
            data["createSource"] = creator.to_dict()
        if attachment:
            data.update(await self._process_attachment(message, attachment, from_user))
        async with self._ryver._session.post(url, json=data) as resp:
            return (await resp.json())["d"]["id"]

    async def get_topics(self, archived: bool = False, top: int = -1, skip: int = 0) -> typing.AsyncIterator[Topic]:
        """
        Get all the topics in this chat.

        :param archived: If True, only include archived topics in the results, otherwise, only include non-archived topics.
        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results.
        :return: An async iterator for the topics of this chat.
        """
        url = self.get_api_url(
            f"Post.Stream(archived={'true' if archived else 'false'})", format="json")
        async for topic in self._ryver.get_all(url=url, top=top, skip=skip):
            yield Topic(self._ryver, topic) #NOSONAR

    async def get_messages(self, count: int, skip: int = 0) -> typing.List[ChatMessage]:
        """
        Get a number of messages (most recent **first**) in this chat.

        :param count: Maximum number of results.
        :param skip: The number of results to skip (optional).
        :return: A list of messages.
        """
        # Interestingly, this does not have the same 50-result restriction as the other API methods...
        url = self.get_api_url(
            "Chat.History()", format="json", top=count, skip=skip)
        async with self._ryver._session.get(url) as resp:
            messages = (await resp.json())["d"]["results"]
        return [ChatMessage(self._ryver, data) for data in messages]

    async def get_message(self, msg_id: str) -> ChatMessage:
        """
        Get a single message from this chat by its ID.

        .. note::
           There is a chance that this method might result in a 404 Not Found for
           messages that were sent recently (such as when using the realtime
           websocket API (:py:class:`pyryver.ryver_ws.RyverWS`) to respond to
           messages), as those messages have not been fully added to Ryver's 
           database yet.

           You can use :py:func:`pyryver.util.retry_until_available()` to wrap
           around this coroutine to get around this.

        :param msg_id: The ID of the chat message to get.
        :return: The message object.
        """
        url = self.get_api_url(
            f"Chat.History.Message(id='{msg_id}')", format="json")
        async with self._ryver._session.get(url) as resp:
            messages = (await resp.json())["d"]["results"]
        return ChatMessage(self._ryver, messages[0])

    async def get_messages_surrounding(self, msg_id: str, before: int = 0, after: int = 0) -> typing.List[ChatMessage]:
        """
        Get a range of messages (most recent **last**) before and after a chat message (given by ID).

        .. warning::
           Before and after cannot exceed 25 messages, otherwise a :py:exc:`aiohttp.ClientResponseError`
           will be raised with the code 400 Bad Request.

        .. note::
           There is a chance that this method might result in a 404 Not Found for
           messages that were sent recently (such as when using the realtime
           websocket API (:py:class:`pyryver.ryver_ws.RyverWS`) to respond to
           messages), as those messages have not been fully added to Ryver's 
           database yet.

           You can use :py:func:`pyryver.util.retry_until_available()` to wrap
           around this coroutine to get around this.

        The message with the given ID is also included as a part of the result.

        :param msg_id: The ID of the message to use as the reference point.
        :param before: How many messages to retrieve before the specified one (optional).
        :param after: How many messages to retrieve after the specified one (optional).
        :return: The messages requested, including the reference point message.
        """
        url = self.get_api_url(
            f"Chat.History.Message(id='{msg_id}',before={before},after={after})", format="json")
        async with self._ryver._session.get(url) as resp:
            messages = (await resp.json())["d"]["results"]
        return [ChatMessage(self._ryver, data) for data in messages]

    async def get_task_board(self) -> typing.Optional["TaskBoard"]:
        """
        Get the task board of this chat.

        If tasks are not set up for this chat, this will return None.

        This method works on users too. If used on a user, it will get their personal
        task board.

        :return: The task board of this chat.
        """
        url = self.get_api_url(action="board")
        async with self._ryver._session.get(url, raise_for_status=False) as resp:
            # No task board
            if resp.status == 404:
                return None
            resp.raise_for_status()
            return TaskBoard(self._ryver, (await resp.json())["d"]["results"])
    
    async def delete_task_board(self) -> bool:
        """
        Delete (or "reset", according to the UI) the task board of this chat.

        This method will not yield an error even if there is no task board set up.
        In those cases, it will simply return false.

        :return: Whether the task board was deleted.
        """
        url = self.get_api_url(action="TaskBoard.Delete()")
        async with self._ryver._session.post(url) as resp:
            return (await resp.json())["d"]
    
    async def create_task_board(self, board_type: str, prefix: typing.Optional[str] = None, 
                                categories: typing.Optional[typing.List[typing.Union[str, typing.Tuple[str, str]]]] = None,
                                uncategorized_name: typing.Optional[str] = None) -> "TaskBoard":
        """
        Create the task board for this chat if it has not yet been set up.

        The board type should be one of the :py:class:`TaskBoard` ``BOARD_TYPE_``
        constants; it specified whether this task board should be a simple list or a
        board with categories.

        You can also specify a list of category names and optional category types to
        pre-populate the task board with categories. Each entry in the list should
        either be a string, which specifies the category name, or a tuple of the name
        and the type of the category (a ``CATEGORY_TYPE_`` constant). The default
        category type is :py:attr:`TaskCategory.CATEGORY_TYPE_OTHER`.

        An "uncategorized" category is always automatically added. Therefore, the type
        :py:attr:`TaskCategory.CATEGORY_TYPE_UNCATEGORIZED` cannot be used in the list.
        You can, however, change the name of the default "Uncategorized" category by
        specifying ``uncategorized_name``.

        Categories should not be specified if the type of the task board is 
        :py:attr:`TaskBoard.BOARD_TYPE_LIST`.

        :param board_type: The type of the task board.
        :param prefix: The task prefix (optional).
        :param categories: A list of categories and optional types to pre-populate the
                           task board with (see above) (optional).
        :param uncategorized_name: The name for the default "Uncategorized" category.
        """
        data = {
            "board": {
                "type": board_type,
                "prefix": prefix
            }
        }
        if categories or uncategorized_name is not None:
            cats = [
                {
                    "categoryType": TaskCategory.CATEGORY_TYPE_UNCATEGORIZED,
                    "name": uncategorized_name if uncategorized_name is not None else "Uncategorized",
                    "position": 0,
                }
            ]
            if categories:
                for i, category in enumerate(categories):
                    if isinstance(category, tuple):
                        cats.append({
                            "categoryType": category[1],
                            "name": category[0],
                            "position": i + 1,
                        })
                    else:
                        cats.append({
                            "categoryType": TaskCategory.CATEGORY_TYPE_OTHER,
                            "name": category,
                            "position": i + 1,
                        })
            data["board"]["categories"] = {
                "results": cats
            }
        url = self.get_api_url(action="TaskBoard.Create()")
        async with self._ryver._session.post(url, json=data) as resp:
            return TaskBoard(self._ryver, (await resp.json()))
    
    async def delete_avatar(self) -> None:
        """
        Delete the avatar of this chat.
        """
        url = self.get_api_url(action="Contatta.Storage.DeleteAvatars()")
        await self._ryver._session.post(url)
    
    async def set_avatar(self, filename: str, filedata: typing.Any, filetype: typing.Optional[str] = None) -> None:
        """
        Set the avatar of this chat.

        A wrapper for :py:meth:`Storage.make_avatar_of()` and :py:meth:`Ryver.upload_file()`.

        :param filename: The filename of the image.
        :param filedata: The image's raw data, sent directly to :py:meth:`aiohttp.FormData.add_field`.
        :param filetype: The MIME type of the file.
        """
        img = await self._ryver.upload_file(filename, filedata, filetype)
        await img.make_avatar_of(self)


class User(Chat):
    """
    A Ryver user.

    :cvar ROLE_USER: Regular organization member. Admins also have this role in addition to ``ROLE_ADMIN``.
    :cvar ROLE_ADMIN: An org admin.
    :cvar ROLE_GUEST: A guest.

    :cvar USER_TYPE_MEMBER: A member.
    :cvar USER_TYPE_GUEST: A guest.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_USER

    ROLE_USER = "ROLE_USER"
    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_GUEST = "ROLE_GUEST"

    USER_TYPE_MEMBER = "member"
    USER_TYPE_GUEST = "guest"

    def get_username(self) -> str:
        """
        Get the username of this user.

        :return: The username of this user.
        """
        return self._data["username"]

    def get_display_name(self) -> str:
        """
        Get the display name of this user.

        :return: The display name of this user.
        """
        return self._data["displayName"]

    def get_name(self) -> str:
        """
        Get the display name of this user (same as the display name).

        :return: The name of this user.
        """
        return self._data["displayName"]

    def get_role(self) -> str:
        """
        Get this user's role in their profile.

        .. note:: 
           This is different from :py:meth:`get_roles()`. While this one gets the "Role"
           of the user from the profile, ``get_roles()`` gets the user's roles in the
           organization (user, guest, admin).

        :return: The user's "Role" as described in their profile.
        """
        return self._data["description"]

    def get_about(self) -> str:
        """
        Get this user's About.

        :return: The user's "About" as described in their profile.
        """
        return self._data["aboutMe"]

    def get_time_zone(self) -> str:
        """
        Get this user's Time Zone.

        :return: The user's time zone.
        """
        return self._data["timeZone"]

    def get_email_address(self) -> str:
        """
        Get this user's Email Address.

        :return: The user's email address.
        """
        return self._data["emailAddress"]

    def get_activated(self) -> bool:
        """
        Get whether this user's account is activated.

        :return: Whether this user's account is activated (enabled).
        """
        return self._data["active"]

    def get_roles(self) -> typing.List[str]:
        """
        Get this user's role in the organization.

        .. note:: 
           This is different from :py:meth:`get_role()`. While this one gets the user's
           roles in the organization (user, guest, admin), ``get_role()`` gets the
           user's role from their profile.

        :return: The user's roles in the organization.
        """
        return self._data["roles"]
    
    def get_user_type(self) -> str:
        """
        Get the type of this user (member or guest).

        The returned value will be either :py:attr:`User.USER_TYPE_MEMBER` or
        :py:attr:`User.USER_TYPE_GUEST`.

        :return: The type of the user.
        """
        return self._data["type"]

    def is_admin(self) -> bool:
        """
        Get whether this user is an org admin.

        :return: Whether the user is an org admin.
        """
        return User.ROLE_ADMIN in self.get_roles()
    
    def accepted_invite(self) -> bool:
        """
        Get whether this user has accepted their user invite.

        :return: Whether the user has accepted their invite.
        """
        return not self._data["newUser"]

    async def set_profile(self, display_name: typing.Optional[str] = None, role: typing.Optional[str] = None,
                          about: typing.Optional[str] = None) -> None:
        """
        Update this user's profile.

        If any of the arguments are None, they will not be changed.

        .. note::
           This also updates these properties in this object.

        :param display_name: The user's new display_name.
        :param role: The user's new role, as described in :py:meth:`get_role()`.
        :param about: The user's new "about me" blurb.
        """
        url = self.get_api_url()
        data = {
            "aboutMe": about if about is not None else self.get_about(),
            "description": role if role is not None else self.get_role(),
            "displayName": display_name if display_name is not None else self.get_display_name(),
        }
        await self._ryver._session.patch(url, json=data)

        self._data["aboutMe"] = data["aboutMe"]
        self._data["description"] = data["description"]
        self._data["displayName"] = data["displayName"]

    async def set_activated(self, activated: bool) -> None:
        """
        Activate or deactivate the user. Requires admin.

        .. note::
           This also updates these properties in this object.
        """
        url = self.get_api_url(
            f"User.Active.Set(value='{'true' if activated else 'false'}')")
        await self._ryver._session.post(url)
        self._data["active"] = activated

    async def set_org_role(self, role: str) -> None:
        """
        Set a user's role in this organization, as described in :py:meth:`get_roles()`.

        This can be either ``ROLE_USER``, ``ROLE_ADMIN`` or ``ROLE_GUEST``.

        .. note::
           Although for org admins, :py:meth:`get_roles()` will return both
           ``ROLE_USER`` and ``ROLE_ADMIN``, to make someone an org admin you only
           need to pass ``ROLE_ADMIN`` into this method.

        .. note::
           This also updates these properties in this object.
        """
        url = self.get_api_url(f"User.Role.Set(role='{role}')")
        await self._ryver._session.post(url)

        self._data["roles"] = [role]
        # Admins also have the normal user role
        if role == User.ROLE_ADMIN:
            self._data["roles"].append(User.ROLE_USER)
    
    async def add_to_chat(self, chat: "GroupChat", role: typing.Optional[str] = None) -> None:
        """
        Add a user to a forum/team.

        The ``role`` should be either :py:attr:`GroupChatMember.ROLE_MEMBER` or
        :py:attr:`GroupChatMember.ROLE_ADMIN`. By default, new members are invited
        as normal members.

        :param chat: The forum/team to add to.
        :param role: The role to invite the user as (member or admin) (optional, defaults to member).
        """
        url = self.get_api_url(action="User.AddToTeams()")
        data = {
            "teams": [
                {
                    "id": chat.get_id(),
                    "role": role if role is not None else GroupChatMember.ROLE_MEMBER
                }
            ]
        }
        await self._ryver._session.post(url, json=data)

    async def create_topic(self, from_user: "User", subject: str, body: str, stickied: bool = False,
                           attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = None,
                           creator: typing.Optional[Creator] = None) -> Topic:
        """
        Create a topic in this user's DMs.

        Returns the topic created.

        .. tip::
           To attach files to the topic, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the files you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for link attachments.

        :param from_user: The user that will create the topic; must be the same as the logged-in user.
        :param subject: The subject (or title) of the new topic.
        :param body: The contents of the new topic.
        :param stickied: Whether to sticky (pin) this topic to the top of the list (optional, default False).
        :param attachments: A number of attachments for this topic (optional).
        :param creator: The overridden creator; optional, if unset uses the logged-in user's profile.
        :return: The created topic.
        """
        url = self._ryver.get_api_url(TYPE_TOPIC)
        data = {
            "body": body,
            "subject": subject,
            "outAssociations": {
                "results": [
                    {
                        "inSecured": True,
                        "inType": self.get_entity_type(),
                        "inId": self.get_id(),
                        "inName": self.get_display_name(),
                    },
                    {
                        "inSecured": True,
                        "inType": from_user.get_entity_type(),
                        "inId": from_user.get_id(),
                        "inName": from_user.get_display_name(),
                    }
                ]
            },
            "recordType": "note",
            "stickied": stickied
        }
        if creator is not None:
            data["createSource"] = creator.to_dict()
        if attachments:
            data["attachments"] = {
                "results": [attachment.get_file().get_raw_data() if isinstance(attachment, Storage) 
                            and attachment.get_storage_type() == Storage.STORAGE_TYPE_FILE 
                            else attachment.get_raw_data() for attachment in attachments]
            }
        async with self._ryver._session.post(url, json=data) as resp:
            return Topic(self._ryver, (await resp.json())["d"]["results"])


class GroupChatMember(Object):
    """
    A member in a forum or team.

    This class can be used to tell whether a user is an admin of their forum/team.

    :cvar ROLE_MEMBER: Regular chat member. Note: This member could also be an org admin.
    :cvar ROLE_ADMIN: Forum/team admin.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_GROUPCHAT_MEMBER

    ROLE_MEMBER = "ROLE_TEAM_MEMBER"
    ROLE_ADMIN = "ROLE_TEAM_ADMIN"

    def get_role(self) -> str:
        """
        Get the role of this member.

        This will be one of the ``ROLE_`` constants in this class.

        :return: The role of this member.
        """
        return self._data["role"]

    async def as_user(self) -> User:
        """
        Get this member as a :py:class:`User` object.

        :return: The member as a ``User`` object.
        """
        return await self.get_deferred_field("member", TYPE_USER)
    
    def get_name(self) -> str:
        """
        Get the display name of this member.
        """
        return self._data["extras"]["displayName"]

    def is_admin(self) -> bool:
        """
        Get whether this member is an admin of their forum/team.

        .. warning::
           This method does not check for org admins.

        :return: Whether this user is a forum admin/team admin.
        """
        return GroupChatMember.ROLE_ADMIN == self.get_role()
    
    async def remove(self) -> None:
        """
        Remove this member from the forum/team.
        """
        url = self.get_api_url(action="Remove()")
        await self._ryver._session.post(url)
    
    async def set_role(self, role: str) -> None:
        """
        Set the role of this member (regular member or admin).

        The role should be one of the ``ROLE_`` constants in this class.

        .. note::
           This will also update the role stored in this object.

        :param role: The new role of the member.
        """
        url = self.get_api_url(action=f"Role.Set(role='{role}')")
        await self._ryver._session.post(url)
        self._data["role"] = role


class GroupChat(Chat):
    """
    A Ryver team or forum.
    """

    __slots__ = ()

    _OBJ_TYPE = "__groupChat"

    def get_name(self) -> str:
        """
        Get the name of this chat.

        :return: The name of this forum/team.
        """
        return self._data["name"]

    def get_nickname(self) -> str:
        """
        Get the nickname of this chat.

        The nickname is a unique identifier that can be used to refer to the chat across Ryver.

        :return: The nickname of this forum/team.
        """
        return self._data["nickname"]
    
    def has_chat(self) -> bool:
        """
        Get whether this forum/team has a chat tab.

        :return: Whether there is a chat tab for this forum/team.
        """
        return "chat" in self._data["tabs"]
    
    def has_topics(self) -> bool:
        """
        Get whether this forum/team has a topics tab.

        :return: Whether there is a topics tab for this forum/team.
        """
        return "post" in self._data["tabs"]
    
    def has_tasks(self) -> bool:
        """
        Get whether this forum/team has a tasks tab.

        :return: Whether there is a tasks tab for this forum/team.
        """
        return "task" in self._data["tabs"]

    def does_announce_topics(self) -> bool:
        """
        Get whether new topics are announced with a chat message.

        :return: Whether new topics are announced with a chat message.
        """
        return self._data["sharePosts"]
    
    def does_announce_tasks(self) -> bool:
        """
        Get whether new tasks are announced with a chat message.

        :return: Whether new tasks are announced with a chat message.
        """
        return self._data["shareTasks"]
    
    def is_archived(self) -> bool:
        """
        Get whether this team/forum is archived.

        :return: Whether the team/forum is archived.
        """
        return not self._data["active"]

    async def get_members(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator[GroupChatMember]:
        """
        Get all the members of this chat.

        .. note::
           This gets the members as :py:class:`GroupChatMember` objects, which contain
           additional info such as whether the user is an admin of this chat.

           To get the :py:class:`User` object, use :py:meth:`GroupChatMember.as_user()`.

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results.
        :return: An async iterator for the members of this chat.
        """
        url = self.get_api_url("members", expand="member")
        async for member in self._ryver.get_all(url=url, top=top, skip=skip):
            yield GroupChatMember(self._ryver, member) #NOSONAR

    async def get_member(self, user: typing.Union[int, User]) -> typing.Optional[GroupChatMember]:
        """
        Get a member using either a User object or user ID.

        .. note::
           This gets the member as a :py:class:`GroupChatMember` object, which contain
           additional info such as whether the user is an admin of this chat.

        .. note::
           If an ID is provided, it should be the **user** ID of this member, not the
           groupchat member ID.

        If the user is not found, this method will return None.

        :param user: The user, or the ID of the user.
        :return: The member, or None if not found.
        """
        user_id = user.get_id() if isinstance(user, User) else user
        url = self.get_api_url("members", expand="member",
                               filter=f"(member/id eq {user_id})")
        async with self._ryver._session.get(url) as resp:
            member = (await resp.json())["d"]["results"]
        return GroupChatMember(self._ryver, member[0]) if member else None
    
    async def add_member(self, user: User, role: str = None) -> None:
        """
        Add a member to this forum or team.

        This is a wrapper for :py:meth:`User.add_to_chat()`.

        The ``role`` should be either :py:attr:`GroupChatMember.ROLE_MEMBER` or
        :py:attr:`GroupChatMember.ROLE_ADMIN`. By default, new members are invited
        as normal members.

        :param user: The user to add.
        :param role: The role to invite the user as (member or admin) (optional).
        """
        await user.add_to_chat(self, role)

    async def remove_member(self, user: typing.Union[int, User]) -> None:
        """
        Remove a user from this forum/team.

        Either a user ID or a user object can be used.

        If the user is not in this forum/team, this method will do nothing.

        :param user: The user or the ID of the user to remove.
        """
        member = await self.get_member(user)
        if member is not None:
            await member.remove()

    async def create_topic(self, subject: str, body: str, stickied: bool = False,
                           attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = None,
                           creator: typing.Optional[Creator] = None) -> Topic:
        """
        Create a topic in this chat.

        Returns the topic created.

        .. tip::
           To attach files to the topic, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the files you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for link attachments.

        .. versionchanged:: 0.4.0
           Switched the order of attachments and creator for consistency.

        :param subject: The subject (or title) of the new topic.
        :param body: The contents of the new topic.
        :param stickied: Whether to sticky (pin) this topic to the top of the list (optional, default False).
        :param attachments: A number of attachments for this topic (optional).
        :param creator: The overridden creator; optional, if unset uses the logged-in user's profile.
        :return: The created topic.
        """
        url = self._ryver.get_api_url(TYPE_TOPIC)
        data = {
            "body": body,
            "subject": subject,
            "outAssociations": {
                "results": [
                    {
                        "inSecured": True,
                        "inType": self.get_entity_type(),
                        "inId": self.get_id()
                    }
                ]
            },
            "recordType": "note",
            "stickied": stickied
        }
        if creator is not None:
            data["createSource"] = creator.to_dict()
        if attachments:
            data["attachments"] = {
                "results": [attachment.get_file().get_raw_data() if isinstance(attachment, Storage) 
                            and attachment.get_storage_type() == Storage.STORAGE_TYPE_FILE 
                            else attachment.get_raw_data() for attachment in attachments]
            }
        async with self._ryver._session.post(url, json=data) as resp:
            return Topic(self._ryver, (await resp.json())["d"]["results"])
    
    async def change_settings(self, chat: typing.Optional[bool] = NO_CHANGE, topics: typing.Optional[bool] = NO_CHANGE,
                              tasks: typing.Optional[bool] = NO_CHANGE, announce_topics: typing.Optional[bool] = NO_CHANGE,
                              announce_tasks: typing.Optional[bool] = NO_CHANGE) -> None:
        """
        Change the settings of this forum/team.

        .. note::
           The settings here contain only the settings in the "Settings" tab in the UI.
        
           This method also updates these properties in this object.

        If any parameters are unspecified, :py:const:`NO_CHANGE`, or ``None``, they will
        be left as-is.
        
        :param chat: Whether there should be a chat tab for this forum/team (optional).
        :param topics: Whether there should be a topics tab for this forum/team (optional).
        :param tasks: Whether there should be a tasks tab for this form/team (optional).
        :param announce_topics: Whether new topics should be announced in the chat (optional).
        :param announce_tasks: Whether new tasks should be announced in the chat (optional).
        """
        url = self.get_api_url()
        tabs = self._data["tabs"] # type: typing.List[str]
        # Update the tabs
        if chat is not NO_CHANGE and chat is not None:
            if chat and "chat" not in tabs:
                tabs.append("chat")
            elif not chat and "chat" in tabs:
                tabs.remove("chat")
        if topics is not NO_CHANGE and topics is not None:
            if topics and "post" not in tabs:
                tabs.append("post")
            elif not topics and "post" in tabs:
                tabs.remove("post")
        if tasks is not NO_CHANGE and tasks is not None:
            if tasks and "task" not in tabs:
                tabs.append("task")
            elif not tasks and "task" in tabs:
                tabs.remove("task")
        data = {
            "tabs": tabs
        }
        if announce_topics is not NO_CHANGE and announce_topics is not None:
            data["sharePosts"] = announce_topics
        if announce_tasks is not NO_CHANGE and announce_tasks is not None:
            data["shareTasks"] = announce_tasks
        await self._ryver._session.patch(url, json=data)
        self._data.update(data)
    
    async def set_archived(self, archived: bool) -> None:
        """
        Set whether this team/forum is archived.

        .. note::
           This method also updates the archived property of this object.

        :param archived: Whether this team/forum should be archived.
        """
        url = self.get_api_url()
        data = {
            "active": not archived
        }
        await self._ryver._session.patch(url, json=data)
        self._data["active"] = not archived
    
    async def delete(self) -> None:
        """
        Delete this forum/team.

        As with most things, once it's deleted, there's no way to go back!
        """
        url = self.get_api_url()
        await self._ryver._session.delete(url)
    
    async def join(self) -> None:
        """
        Join this forum/team as the current logged in user.
        """
        await self._ryver._session.post(self.get_api_url("Team.Join()", format="json"))
    
    async def leave(self) -> None:
        """
        Leave this forum/team as the current logged in user.

        .. note::
           This is not the same as selecting "Close and keep closed" in the UI. With
           this, the user will no longer show up in the members list of the forum/team,
           whereas "Close and keep closed" will still keep the user in the forum/team and
           only update the notification settings.
        """
        await self._ryver._session.post(self.get_api_url("Team.Leave()", format="json"))


class Forum(GroupChat):
    """
    A Ryver forum.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_FORUM


class Team(GroupChat):
    """
    A Ryver team.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TEAM


class TaskBoard(Object):
    """
    A Ryver task board.

    :cvar BOARD_TYPE_BOARD: A task board with categories.
    :cvar BOARD_TYPE_LIST: A task list (i.e. a task board without categories).
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TASK_BOARD

    BOARD_TYPE_BOARD = "board"
    BOARD_TYPE_LIST = "list"

    def get_name(self) -> str:
        """
        Get the name of this task board.

        This will be the same as the name of the forum/team/user the task board is
        associated with.

        :return: The name of the task board.
        """
        return self._data["name"]

    def get_board_type(self) -> str:
        """
        Get the type of this task board.

        Returns one of the ``BOARD_TYPE_`` constants in this class.

        ``BOARD_TYPE_BOARD`` is a task board with categories, while ``BOARD_TYPE_LIST``
        is a task list without categories.

        Not to be confused with :py:meth:`Object.get_type()`.

        :return: The type of this task board.
        """
        return self._data["type"]

    def get_prefix(self) -> str:
        """
        Get the prefix for this task board.

        The prefix can be used to reference tasks across Ryver using the #PREFIX-ID
        syntax.

        If a task board does not have task IDs set up, this will return None.

        :return: The task prefix for this task board.
        """
        return self._data["shortPrefix"]

    async def get_categories(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator["TaskCategory"]:
        """
        Get all the categories in this task board.

        Even if this task board has no categories (a list), this method will still
        return a single category, "Uncategorized".

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results (optional).
        :return: An async iterator for the categories in this task board.
        """
        url = self.get_api_url(action="categories")
        async for category in self._ryver.get_all(url=url, top=top, skip=skip):
            yield TaskCategory(self._ryver, category) #NOSONAR

    async def create_category(self, name: str, done: bool = False) -> "TaskCategory":
        """
        Create a new task category in this task board.

        :param name: The name of this category.
        :param done: Whether tasks moved to this category should be marked as done.
        :return: The created category.
        """
        url = self._ryver.get_api_url(TYPE_TASK_CATEGORY)
        data = {
            "board": {
                "id": self.get_id()
            },
            "name": name,
        }
        if done:
            data["categoryType"] = "done"
        async with self._ryver._session.post(url, json=data) as resp:
            return TaskCategory(self._ryver, (await resp.json())["d"]["results"])

    async def get_tasks(self, archived: typing.Optional[bool] = None, top: int = -1, skip: int = 0) -> typing.AsyncIterator["Task"]:
        """
        Get all the tasks in this task board.

        If ``archived`` is unspecified or None, all tasks will be retrieved.
        If ``archived`` is either True or False, only tasks that are archived or
        unarchived are retrieved, respectively.

        This will not retrieve sub-tasks (checklist items).

        :param archived: If True or False, only retrieve tasks that are archived or unarchived; if None, retrieve all tasks (optional).
        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results (optional).
        :return: An async iterator for the tasks in this task board.
        """
        if archived is None:
            url = self.get_api_url(action="tasks")
        else:
            url = self.get_api_url(action="tasks",
                                   filter=f"(archived eq {'true' if archived else 'false'} and parent eq null)")
        async for task in self._ryver.get_all(url=url, top=top, skip=skip):
            yield Task(self._ryver, task) #NOSONAR

    async def create_task(self, subject: str, body: str = "", category: typing.Optional["TaskCategory"] = None,
                          assignees: typing.Optional[typing.Iterable[User]] = None, due_date: typing.Optional[str] = None,
                          tags: typing.Optional[typing.Union[typing.List[str], typing.List[TaskTag]]] = None,
                          checklist: typing.Optional[typing.Iterable[str]] = None,
                          attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = None) -> "Task":
        """
        Create a task in this task board.

        If the category is None, this task will be put in the "Uncategorized" category.
        For list type task boards, the category can be left as None.

        .. tip::
           To attach files to the task, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the files you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for link attachments.

        .. tip::
           You can use :py:meth:`pyryver.util.datetime_to_iso8601()` to turn datetime
           objects into timestamps that Ryver will accept.

           Note that timezone info **must** be present in the timestamp. Otherwise, this
           will result in a 400 Bad Request.

        :param subject: The subject, or title of the task.
        :param body: The body, or description of the task (optional).
        :param category: The category of the task; if None, the task will be uncategorized (optional).
        :param assignees: A list of users to assign for this task (optional).
        :param due_date: The due date, as an ISO 8601 formatted string **with a timezone offset** (optional).
        :param tags: A list of tags of this task (optional). Can either be a list of strings or a list of ``TaskTag``s.
        :param checklist: A list of strings which are used as the item names for the checklist of this task (optional).
        :param attachments: A list of attachments for this task (optional).
        :return: The created task.
        """
        data = {
            "board": {
                "id": self.get_id()
            },
            "subject": subject,
            "body": body,
        }
        if category is not None:
            data["category"] = {
                "id": category.get_id()
            }
        if assignees:
            data["assignees"] = {
                "results": [{"__descriptor": user.get_name(), "id": user.get_id()} for user in assignees]
            }
        if tags:
            # Convert TaskTags to strings
            if isinstance(tags[0], TaskTag):
                tags = [tag.get_name() for tag in tags]
            data["tags"] = tags
        if attachments:
            data["attachments"] = {
                "results": [{
                    "id": attachment.get_id() if isinstance(attachment, File)
                          else attachment.get_content_id()
                } for attachment in attachments]
            }
        if due_date is not None:
            data["dueDate"] = due_date
        if checklist:
            data["subTasks"] = {
                "results": [{"subject": subject} for subject in checklist]
            }
        url = self._ryver.get_api_url(TYPE_TASK)
        async with self._ryver._session.post(url, json=data) as resp:
            return Task(self._ryver, (await resp.json())["d"]["results"])
    
    async def get_chat(self) -> Chat:
        """
        Get the chat this task board is in.

        If this task board is a public task board in a forum or team, a
        :py:class:`GroupChat` object will be returned. If this task board is a personal
        (user) task board, a :py:class:`User` object will be returned.

        .. note::
           API Detail: Although public task boards can be in either a forum or a team,
           :py:class:`GroupChat` objects returned by this method will *always* be
           instances of :py:class:`Team`, even if the task board exists in a forum.
           There seems to be no way of determining whether the returned chat is actually
           a forum or a team. However, as both forums/teams have the exact same methods,
           this detail shouldn't matter.

        :return: The forum/team/user this task board is in.
        """
        try:
            return await self.get_deferred_field("team", TYPE_TEAM)
        except ValueError:
            return await self.get_deferred_field("user", TYPE_USER)


class TaskCategory(Object):
    """
    A category in a task board.

    :cvar CATEGORY_TYPE_UNCATEGORIZED: The "Uncategorized" category, created by the system
                                       (present in all task boards regardless of whether it is shown).
    :cvar CATEGORY_TYPE_DONE: A user-created category in which all tasks are marked as done.
    :cvar CATEGORY_TYPE_OTHER: Other categories (user-created and not marked as done).
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TASK_CATEGORY

    CATEGORY_TYPE_UNCATEGORIZED = "uncategorized"
    CATEGORY_TYPE_DONE = "done"
    CATEGORY_TYPE_OTHER = "user"

    def get_name(self) -> str:
        """
        Get the name of this category.

        :return: The name of this category.
        """
        return self._data["name"]

    def get_position(self) -> int:
        """
        Get the position of this category in this task board.

        Positions are numbered from left to right.

        .. note::
           The first user-created category that is shown in the UI has a position of 1.
           This is because the "Uncategorized" category, which is present in all task
           boards, always has a position of 0, even when it's not shown (when there are
           no uncategorized tasks).

        :return: The position of this category.
        """
        return self._data["position"]

    def get_category_type(self) -> str:
        """
        Get the type of this task category.

        Returns one of the ``CATEGORY_TYPE_`` constants in this class.

        :return: The type of this category.
        """
        return self._data["categoryType"]

    async def get_task_board(self) -> TaskBoard:
        """
        Get the task board that contains this category.

        :return: The task board.
        """
        return await self.get_deferred_field("board", TYPE_TASK_BOARD)

    async def edit(self, name: typing.Optional[str] = NO_CHANGE, done: typing.Optional[bool] = NO_CHANGE) -> None:
        """
        Edit this category.

        .. note::
           This method also updates these properties in this object.

        .. warning::
           ``done`` should **never** be set for the "Uncategorized" category, as its
           type cannot be modified. If set, a ``ValueError`` will be raised.

        If any parameters are unspecified or :py:const:`NO_CHANGE`, they will be left
        as-is. Passing ``None`` for parameters for which ``None`` is not a valid value
        will also result in the value being unchanged.

        :param name: The name of this category (optional).
        :param done: Whether tasks moved to this category should be marked as done (optional).
        :raises ValueError: If attempting to modify the type of the "Uncategorized" category.
        """
        url = self.get_api_url()
        data = {}
        if name is not NO_CHANGE and name is not None:
            data["name"] = name
        if done is not NO_CHANGE and done is not None:
            if self.get_category_type() == TaskCategory.CATEGORY_TYPE_UNCATEGORIZED:
                raise ValueError("Cannot modify type of the 'Uncategorized' category!")
            if done:
                data["categoryType"] = TaskCategory.CATEGORY_TYPE_DONE
            else:
                data["categoryType"] = TaskCategory.CATEGORY_TYPE_OTHER
        await self._ryver._session.patch(url, json=data)
        self._data.update(data)

    async def delete(self, move_to: typing.Optional["TaskCategory"] = None) -> None:
        """
        Delete this category.

        If ``move_to`` is specified, the tasks that are in this category will be moved
        into the specified category and not archived. Otherwise, the tasks will be
        archived.

        :param move_to: Another category to move the tasks in this category to (optional).
        """
        if move_to is None:
            url = self.get_api_url(action="TaskCategory.Delete(archive=true)")
        else:
            url = self.get_api_url(action=f"TaskCategory.Delete(moveTo={move_to.get_id()},archive=true)")
        await self._ryver._session.post(url)

    async def archive(self, completed_only: bool = False) -> None:
        """
        Archive either all or only completed tasks in this category.

        .. deprecated:: 0.4.0
           Use :py:meth:`TaskCategory.archive_tasks()` instead. The functionality is
           unchanged but the name is less misleading.

        .. note::
           This archives the tasks in this category, not the category itself.

        :param completed_only: Whether to only archive completed tasks (optional).
        """
        await self.archive_tasks(completed_only)

    async def archive_tasks(self, completed_only: bool = False) -> None:
        """
        Archive either all or only completed tasks in this category.

        :param completed_only: Whether to only archive completed tasks (optional).
        """
        url = self.get_api_url(
            action=f"TaskCategory.Archive(completeOnly={'true' if completed_only else 'false'})")
        await self._ryver._session.post(url)

    async def move_position(self, position: int) -> None:
        """
        Move this category's display position in the UI.

        .. note::
           This also updates the position property of this object.

           The first user-created category that is shown in the UI has a position of 1.
           This is because the "Uncategorized" category, which is present in all task
           boards, always has a position of 0, even when it's not shown (when there are
           no uncategorized tasks). 

           Therefore, no user-created task category can ever be moved to position 0,
           and the "Uncategorized" category should never be moved.

        :param position: The new display position.
        """
        url = self.get_api_url(
            action=f"TaskCategory.Move(position={position})")
        await self._ryver._session.post(url)
        self._data["position"] = position

    async def move_tasks(self, category: "TaskCategory", completed_only: bool = False) -> None:
        """
        Move either all or only completed tasks in this category to another category.

        :param category: The category to move to.
        :param completed_only: Whether to only move completed tasks (optional).
        """
        url = self.get_api_url(
            action=f"TaskCategory.MoveTasks(moveTo={category.get_id()},completeOnly={'true' if completed_only else 'false'})")
        await self._ryver._session.post(url)

    async def get_tasks(self, archived: typing.Optional[bool] = None, top: int = -1, skip: int = 0) -> typing.AsyncIterator["Task"]:
        """
        Get all the tasks in this category.

        If ``archived`` is unspecified or None, all tasks will be retrieved.
        If ``archived`` is either True or False, only tasks that are archived or
        unarchived are retrieved, respectively.

        This will not retrieve sub-tasks (checklist items).

        :param archived: If True or False, only retrieve tasks that are archived or unarchived; if None, retrieve all tasks (optional).
        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results (optional).
        :return: An async iterator for the tasks in this category.
        """
        if archived is None:
            url = self.get_api_url(action="tasks")
        else:
            url = self.get_api_url(
                action="tasks", filter=f"(archived eq {'true' if archived else 'false'} and parent eq null)")
        async for task in self._ryver.get_all(url, top, skip):
            yield Task(self._ryver, task) #NOSONAR


class Task(PostedMessage):
    """
    A Ryver task.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TASK

    def is_archived(self) -> bool:
        """
        Get whether this task has been archived.

        :return: Whether this task has been archived.
        """
        return self._data["archived"]

    def get_subject(self) -> str:
        """
        Get the subject (title) of this task.

        :return: The subject of this task.
        """
        return self._data["subject"]

    def get_due_date(self) -> typing.Optional[str]:
        """
        Get the due date as an ISO 8601 timestamp.

        If there is no due date, this method will return None.

        .. tip::
           You can use :py:meth:`pyryver.util.iso8601_to_datetime()` to convert the 
           timestamps returned by this method into a datetime.

        :return: The due date of this task.
        """
        return self._data["dueDate"]

    def get_complete_date(self) -> typing.Optional[str]:
        """
        Get the complete date as an ISO 8601 timestamp.

        If the task has not been completed, this method will return None.

        .. tip::
           You can use :py:meth:`pyryver.util.iso8601_to_datetime()` to convert the 
           timestamps returned by this method into a datetime.

        :return: The completion date of this task.
        """
        return self._data["completeDate"]

    def is_completed(self) -> bool:
        """
        Get whether this task has been completed.

        :return: Whether this task has been completed.
        """
        return self.get_complete_date() is not None

    def get_short_repr(self) -> typing.Optional[str]:
        """
        Get the short representation of this task. 

        This is can be used to reference this task across Ryver.
        It has the form PREFIX-ID, and is also unique across the entire organization.

        If the task board does not have prefixes set up, this will return None.

        :return: The unique short representation of this task.
        """
        return self._data["short"]

    def get_position(self) -> int:
        """
        Get the position of this task in its category or the task list.

        The first task has a position of 0.

        :return: The position of this task in its category.
        """
        return self._data["position"]

    def get_comments_count(self) -> int:
        """
        Get how many comments this task has received.

        :return: The number of comments this task has received.
        """
        return self._data["commentsCount"]

    def get_attachments_count(self) -> int:
        """
        Get how many attachments this task has.

        :return: The number of attachments this task has.
        """
        return self._data["attachmentsCount"]

    def get_tags(self) -> typing.List[str]:
        """
        Get all the tags of this task.

        .. note::
           The tags are returned as a list of strings, not a list of ``TaskTag``s.

        :return: All the tags of this task, as strings.
        """
        return self._data["tags"]

    async def get_task_board(self) -> TaskBoard:
        """
        Get the task board this task is in.

        :return: The task board containing this task.
        """
        return await self.get_deferred_field("board", TYPE_TASK_BOARD)

    async def get_task_category(self) -> TaskCategory:
        """
        Get the category this task is in.

        :return: The category containing this task.
        """
        return await self.get_deferred_field("category", TYPE_TASK_CATEGORY)

    async def get_assignees(self) -> typing.List[User]:
        """
        Get the assignees of this task.

        :return: The assignees of this task,.
        """
        return await self.get_deferred_field("assignees", TYPE_USER)

    async def set_complete_date(self, time: typing.Optional[str] = "") -> None:
        """
        Set the complete date of this task, which also marks whether this task
        is complete.

        An optional completion time can be specified in the form of an ISO 8601
        timestamp with a timezone offset. If not specified or an empty string, the 
        current time will be used.

        .. tip::
           You can use :py:meth:`pyryver.util.datetime_to_iso8601()` to turn datetime
           objects into timestamps that Ryver will accept.

           Note that timezone info **must** be present in the timestamp. Otherwise, this
           will result in a 400 Bad Request.

        If None is used as the time, in addition to clearing the complete date,
        this task will also be un-completed.

        .. note::
           This also updates the complete date property in this object.

           If a time of None is given, this task will be marked as uncomplete.

        :param time: The completion time (optional).
        """
        if time == "":
            time = datetime_to_iso8601(
                datetime.datetime.now(datetime.timezone.utc))
        url = self.get_api_url()
        data = {
            "completeDate": time
        }
        await self._ryver._session.patch(url, json=data)
        self._data["completeDate"] = time

    async def set_due_date(self, time: typing.Optional[str]):
        """
        Set the due date of this task.

        The time must be specified as an ISO 8601 timestamp with a timezone offset.
        It can also be None, in which case there will be no due date.

        .. tip::
           You can use :py:meth:`pyryver.util.datetime_to_iso8601()` to turn datetime
           objects into timestamps that Ryver will accept.

           Note that timezone info **must** be present in the timestamp. Otherwise, this
           will result in a 400 Bad Request.

        .. note::
           This also updates the due date property in this object.

        :param time: The new due date.
        """
        url = self.get_api_url()
        data = {
            "dueDate": time
        }
        await self._ryver._session.patch(url, json=data)
        self._data["dueDate"] = time

    async def complete(self) -> None:
        """
        Mark this task as complete.
        """
        await self.set_complete_date()

    async def uncomplete(self) -> None:
        """
        Mark this task as uncomplete.
        """
        await self.set_complete_date(None)
    
    async def archive(self, archived: bool = True) -> None:
        """
        Archive or un-archive this task.

        :param archived: Whether the task should be archived.
        """
        url = self.get_api_url("Task.Archive()" if archived else "Task.Unarchive()")
        await self._ryver._session.post(url)
    
    async def unarchive(self) -> None:
        """
        Un-archive this task.

        This is the same as calling :py:meth:`Task.archive()` with False.
        """
        await self.archive(False)

    async def move(self, category: TaskCategory, position: int) -> None:
        """
        Move this task to another category or to a different position in the same
        category.

        .. note::
           This also updates the position property of this object.
        """
        url = self.get_api_url(
            action=f"Task.Move(position={position}, category={category.get_id()})")
        await self._ryver._session.post(url)
        self._data["position"] = position

    async def get_checklist(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator["Task"]:
        """
        Get the checklist items of this task (subtasks).

        If this task has no checklist, an empty list will be returned.

        The checklist items are ``Task`` objects; complete or uncomplete those objects
        to change the checklist status.

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results (optional).
        :return: An async iterator for the tasks in the checklist of this task.
        """
        url = self.get_api_url(action="subTasks")
        async for task in self._ryver.get_all(url, top, skip):
            yield Task(self._ryver, task) #NOSONAR

    async def get_parent(self) -> typing.Optional["Task"]:
        """
        Get the parent task of this sub-task (checklist item).

        This only works if this task is an item in another task's checklist.
        Otherwise, this will return None.

        :return: The parent of this sub-task (checklist item), or None if this task is not a sub-task.
        """
        try:
            return await self.get_deferred_field("parent", TYPE_TASK)
        except ValueError:
            return None

    async def add_to_checklist(self, items: typing.Iterable[str]) -> None:
        """
        Add items to this task's checklist.

        :param items: The names of the items to add.
        """
        # Make sure that there is at least one item to add
        # Otherwise the PATCH request will actually erase all existing subtasks
        # as the results array is empty.
        if not items:
            return
        data = {
            "subTasks": {
                "results": [{"subject": subject} for subject in items]
            }
        }
        url = self.get_api_url(
            format="json", select="subTasks", expand="subTasks")
        await self._ryver._session.patch(url, json=data)

    async def set_checklist(self, items: typing.Iterable["Task"]) -> None:
        """
        Set the contents of this task's checklist.

        This will overwrite existing checklist items.

        .. note::
           This method should be used for deleting checklist items only. It cannot be
           used to add new items as the tasks would have to be created first. To add
           new items, use :py:meth:`Task.add_to_checklist()`.

        :param items: The items in the checklist.
        """
        # Note: The official client deletes checklist items another way
        # But I can't get it to work outside the browser
        data = {
            "subTasks": {
                "results": [{"id": item} for item in items]
            }
        }
        url = self.get_api_url()
        await self._ryver._session.patch(url, json=data)
    
    async def edit(self, subject: typing.Optional[str] = NO_CHANGE, body: typing.Optional[str] = NO_CHANGE, 
                   category: typing.Optional["TaskCategory"] = NO_CHANGE, 
                   assignees: typing.Optional[typing.Iterable[User]] = NO_CHANGE,
                   due_date: typing.Optional[str] = NO_CHANGE, 
                   tags: typing.Optional[typing.Union[typing.List[str], typing.List[TaskTag]]] = NO_CHANGE,
                   attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = NO_CHANGE) -> None:
        """
        Edit this task.

        .. note::
           Admins can edit any task regardless of whether they created it.

           The file attachments (if specified) will **replace** all existing attachments.

           Additionally, this method also updates these properties in this object.
        
        .. note::
           While a value of ``None`` for the category in :py:meth:`TaskBoard.create_task()`
           will result in the task being placed in the "Uncategorized" category, 
           ``None`` is not a valid value for the category in this method, and if used
           will result in the category being unmodified.

           This method does not support editing the checklist. To edit the checklist,
           use :py:meth:`Task.get_checklist()`, :py:meth:`Task.set_checklist()` and
           :py:meth:`Task.add_to_checklist()`.

        If any parameters are unspecified or :py:const:`NO_CHANGE`, they will be left
        as-is. Passing ``None`` for parameters for which ``None`` is not a valid value
        will also result in the value being unchanged.

        .. tip::
           To attach files to the task, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the files you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for link attachments.

        .. tip::
           You can use :py:meth:`pyryver.util.datetime_to_iso8601()` to turn datetime
           objects into timestamps that Ryver will accept.

           Note that timezone info **must** be present in the timestamp. Otherwise, this
           will result in a 400 Bad Request.

        :param subject: The subject, or title of the task (optional).
        :param body: The body, or description of the task (optional).
        :param category: The category of the task; if None, the task will be uncategorized (optional).
        :param assignees: A list of users to assign for this task (optional).
        :param due_date: The due date, as an ISO 8601 formatted string **with a timezone offset** (optional).
        :param tags: A list of tags of this task (optional). Can either be a list of strings or a list of ``TaskTag``s.
        :param attachments: A list of attachments for this task (optional).
        """
        data = {}

        if subject is not NO_CHANGE and subject is not None:
            data["subject"] = subject
        if body is not NO_CHANGE and body is not None:
            data["body"] = body
        if category is not NO_CHANGE and category is not None:
            data["category"] = {
                "id": category.get_id()
            }
        if assignees is not NO_CHANGE and assignees is not None:
            data["assignees"] = {
                "results": [{"__descriptor": user.get_name(), "id": user.get_id()} for user in assignees]
            }
        if tags is not NO_CHANGE and tags is not None:
            # Convert TaskTags to strings
            if isinstance(tags[0], TaskTag):
                tags = [tag.get_name() for tag in tags]
            data["tags"] = tags
        if attachments is not NO_CHANGE and attachments is not None:
            data["attachments"] = {
                "results": [{
                    "id": attachment.get_id() if isinstance(attachment, File)
                          else attachment.get_content_id()
                } for attachment in attachments]
            }
        if due_date is not NO_CHANGE and due_date is not None:
            data["dueDate"] = due_date
        url = self.get_api_url()
        await self._ryver._session.patch(url, json=data)
        self._data.update(data)
    
    async def get_comments(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator["TaskComment"]:
        """
        Get all the comments on this task.

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results (optional).
        :return: An async iterator for the comments of this task.
        """
        url = self.get_api_url(action="comments")
        async for comment in self._ryver.get_all(url, top, skip):
            yield TaskComment(self._ryver, comment) #NOSONAR
    
    async def comment(self, message: str, attachments: typing.Optional[typing.Iterable[typing.Union["Storage", "File"]]] = None,
                      creator: typing.Optional[Creator] = None,) -> "TaskComment":
        """
        Comment on this task.

        .. note::
           For unknown reasons, overriding the creator does not seem to work for this method.

        .. tip::
           To attach files to the comment, use :py:meth:`pyryver.ryver.Ryver.upload_file()`
           to upload the files you wish to attach. Alternatively, use
           :py:meth:`pyryver.ryver.Ryver.create_link()` for link attachments.
        
        .. versionchanged:: 0.4.0
           Switched the order of attachments and creator for consistency.

        :param message: The comment's contents.
        :param creator: The overridden creator (optional). **Does not work.**
        :param attachments: A number of attachments for this comment (optional).
        :return: The created comment.
        """
        url = self._ryver.get_api_url(TYPE_TASK_COMMENT, format="json")
        data = {
            "comment": message,
            "task": {
                "id": self.get_id()
            }
        }
        if creator is not None:
            data["createSource"] = creator.to_dict()
        if attachments:
            data["attachments"] = {
                "results": [attachment.get_file().get_raw_data() if isinstance(attachment, Storage) 
                            and attachment.get_storage_type() == Storage.STORAGE_TYPE_FILE 
                            else attachment.get_raw_data() for attachment in attachments]
            }
        async with self._ryver._session.post(url, json=data) as resp:
            return TaskComment(self._ryver, (await resp.json())["d"]["results"])


class TaskComment(PostedComment):
    """
    A comment on a task.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_TASK_COMMENT

    async def get_task(self) -> Task:
        """
        Get the task this comment is on.

        :return: The task this comment is associated with.
        """
        return await self.get_deferred_field("task", TYPE_TASK)


class Notification(Object):
    """
    A Ryver user notification.

    :cvar PREDICATE_MENTION: The user was directly mentioned with an @mention.
    :cvar PREDICATE_GROUP_MENTION: The user was mentioned through @team or @here.
    :cvar PREDICATE_COMMENT: A topic was commented on.
    :cvar PREDICATE_TASK_COMPLETED: A task was completed.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_NOTIFICATION

    PREDICATE_MENTION = "chat_mention"
    PREDICATE_GROUP_MENTION = "group_mention"
    PREDICATE_COMMENT = "commented_on"
    PREDICATE_TASK_COMPLETED = "completed"

    def get_predicate(self) -> str:
        """
        Get the "predicate", or type, of this notification.

        This usually returns one of the ``PREDICATE_`` constants in this class.
        Note that the list currently provided is not exhaustive; this method may
        return a value that isn't one of the constants.

        :return: The predicate of this notification.
        """
        return self._data["predicate"]

    def get_subject_entity_type(self) -> str:
        """
        Get the entity type of the "subject" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        user that did the action which caused this notification.

        :return: The entity type of this notification's subject.
        """
        return self._data["subjectType"]

    def get_subject_id(self) -> int:
        """
        Get the ID of the "subject" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        user that did the action which caused this notification.

        :return: The ID of this notification's subject.
        """
        return self._data["subjectId"]

    def get_subjects(self) -> typing.List[dict]:
        """
        Get the "subjects" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        user that did the action which caused this notification. It is also 
        unknown why this is an array, as it seems to only ever contain one
        element.

        :return: The subjects of this notification.
        """
        return self._data["subjects"]

    def get_object_entity_type(self) -> str:
        """
        Get entity type of the "object" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        target of an @mention for mentions, the topic for topic comments, or the
        task for task activities.

        :return: The entity type of the object of this notification.
        """
        return self._data["objectType"]

    def get_object_id(self) -> int:
        """
        Get the ID of the "object" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        target of an @mention for mentions, the topic for topic comments, or the
        task for task activities.

        :return: The ID of the object of this notification.
        """
        return self._data["objectId"]

    def get_object(self) -> dict:
        """
        Get the "object" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        target of an @mention for mentions, the topic for topic comments, or the
        task for task activities.

        :return: The object of this notification.
        """
        return self._data["object"]

    def get_via_entity_type(self) -> str:
        """
        Get the entity type of the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. For task completions, there is NO via.

        :return: The entity type of the via of this notification.
        """
        return self._data["viaType"]

    def get_via_id(self) -> int:
        """
        Get the ID of the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. For task completions, there is NO via.

        :return: The ID of the via of this notification.
        """
        return self._data["viaId"]

    def get_via(self) -> dict:
        """
        Get the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. For task completions, there is NO via.

        :return: The via of this notification.
        """
        return self._data["via"]

    def get_new(self) -> bool:
        """
        Get whether this notification is new.

        :return: Whether this notification is new.
        """
        return self._data["new"]

    def get_unread(self) -> bool:
        """
        Get whether this notification is unread.

        :return: Whether this notification is unread.
        """
        return self._data["unread"]

    async def set_status(self, unread: bool, new: bool) -> None:
        """
        Set the read/unread and seen/unseen (new) status of this notification.

        .. note:: 
           This also updates these properties in this object.
        """
        data = {
            "unread": unread,
            "new": new,
        }
        url = self.get_api_url(format="json")
        await self._ryver._session.patch(url, json=data)
        self._data["unread"] = unread
        self._data["new"] = new


class File(Object):
    """
    An uploaded file.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_FILE

    def get_title(self) -> str:
        """
        Get the title of this file.

        :return: The title of this file.
        """
        return self._data["title"]

    def get_name(self) -> str:
        """
        Get the name of this file.

        :return: The name of this file.
        """
        return self._data["fileName"]

    def get_size(self) -> int:
        """
        Get the size of this file in bytes.

        :return: The size of the file in bytes.
        """
        return self._data["fileSize"]

    def get_url(self) -> str:
        """
        Get the URL of this file.

        :return: The URL of the file.
        """
        return self._data["url"]

    def get_MIME_type(self) -> str:
        """
        Get the MIME type of this file.

        :return: The MIME type of the file.
        """
        return self._data.get("type", None) or self._data["fileType"]

    def request_data(self) -> aiohttp.ClientResponse:
        """
        Get the file data.

        Returns an aiohttp request response to the file URL.

        :return: An :py:class:`aiohttp.ClientResponse` object representing a request
                 response for the file contents.
        """
        # Use aiohttp.request directly because we don't want to send the auth header
        # Otherwise we'll get a 400
        return aiohttp.request("GET", self.get_url())

    async def download_data(self) -> bytes:
        """
        Download the file data.

        :return: The downloaded file data, as raw bytes.
        """
        # Same as above, this seems to be the only way to send the request without the auth header
        async with aiohttp.request("GET", self.get_url()) as resp:
            resp.raise_for_status()
            return await resp.content.read()

    async def delete(self) -> None:
        """
        Delete this file.
        """
        url = self.get_api_url(format="json")
        await self._ryver._session.delete(url)


class Storage(Object):
    """
    Generic storage (message attachments), e.g. files and links.

    :cvar STORAGE_TYPE_FILE: An uploaded file.
    :cvar STORAGE_TYPE_LINK: A link.
    """

    __slots__ = ()

    _OBJ_TYPE = TYPE_STORAGE

    STORAGE_TYPE_FILE = "file"
    STORAGE_TYPE_LINK = "link"

    def get_storage_type(self) -> str:
        """
        Get the type of this storage object.

        Returns one of the ``STORAGE_TYPE_`` constants in this class.

        Not to be confused with :py:meth:`Object.get_type()`.

        :return: The type of this storage object.
        """
        if "file" in self._data:
            return self._data["file"]["recordType"]
        return self._data["recordType"]

    def get_name(self) -> str:
        """
        Get the name of this storage object.

        :return: The name of this storage object.
        """
        return self._data.get("fileName", None) or self._data["name"]

    def get_size(self) -> str:
        """
        Get the size of the object stored.

        :return: The size of the thing stored.
        """
        return self._data["fileSize"]

    def get_content_id(self) -> int:
        """
        Get the ID of the **contents** of this storage object.

        If a link is stored, then this will return the same value as ``get_id()``.
        If a file is stored, then this will return the ID of the file instead.

        :return: The ID of the contents of this storage object.
        """
        if self.get_storage_type() == Storage.STORAGE_TYPE_FILE:
            return self._data["file"]["id"]
        else:
            return self.get_id()

    def get_content_MIME_type(self) -> str:
        """
        Get the MIME type of the content.

        For links, this will be "application/octet-stream".

        :return: The MIME type of the contents of this storage object.
        """
        return self._data.get("contentType", None) or self._data["type"]

    def get_file(self) -> File:
        """
        Get the file stored.

        .. warning::
           This method will raise a ``KeyError`` if the type of this storage is not
           ``TYPE_FILE``!

        :return: The file stored.
        """
        return File(self._ryver, self._data["file"])

    def get_content_url(self) -> str:
        """
        Get the URL of the contents.

        If a link is stored, then this will be the URL of the link.
        If a file is stored, then this will be the URL of the file contents.

        :return: The content's URL.
        """
        if self.get_storage_type() == Storage.STORAGE_TYPE_FILE:
            return self._data["file"]["url"]
        return self._data["url"]

    async def delete(self) -> None:
        """
        Delete this storage object and the file it contains if there is one.
        """
        url = self._ryver.get_api_url(
            Storage.STORAGE_TYPE_FILE, self.get_content_id(), format="json")
        await self._ryver._session.delete(url)
    
    async def make_avatar_of(self, chat: Chat) -> None:
        """
        Make this image an avatar of a chat.

        :param chat: The chat to change the avatar for.
        :raises ValueError: If the contents of this storage object is not a file.
        """
        url = self.get_api_url(action="Contatta.Storage.MakeAvatars()")
        data = {
            "id": chat.get_id(),
            "type": chat.get_type(),
        }
        await self._ryver._session.post(url, json=data)


def get_obj_by_field(objs: typing.Iterable[Object], field: str, value: typing.Any, case_sensitive: str = True) -> typing.Optional[Object]:
    """
    Gets an object from a list of objects by a field.

    For example, this function can find a chat with a specific nickname in a
    list of chats.

    :param objs: List of objects to search in.
    :param field: The field's name (usually a constant beginning with ``FIELD_`` in
                  :ref:`pyryver.util <util-data-constants>`) within the object's
                  JSON data.
    :param value: The value to look for.
    :param case_sensitive: Whether the search should be case-sensitive. Can be useful
                           for fields such as username or nickname, which are
                           case-insensitive. Defaults to True. If the field value is not
                           a string, it will be ignored.
    :return: The object with the matching field, or None if not found.
    """
    if not case_sensitive and isinstance(value, str):
        value = value.casefold()
    for obj in objs:
        data = obj._data[field]
        if not case_sensitive and isinstance(data, str):
            if data.casefold() == value:
                return obj
        else:
            if obj._data[field] == value:
                return obj
    return None


from .ryver import *  # nopep8

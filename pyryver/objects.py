import aiohttp
import asyncio
import typing
from abc import ABC, abstractmethod
from pyryver.util import *

class Creator:
    """
    A message creator, with a name and an avatar.

    This can be used to override the sender's display name and avatar.

    :param name: The overriden display name
    :param avatar: The overriden avatar (a url to an image)
    """

    def __init__(self, name: str, avatar: str):
        self.name = name
        self.avatar = avatar

    def to_dict(self) -> dict:
        """
        Convert this Creator object to a dictionary to be used in a request.

        Intended for internal use.
        """
        return {
            "displayName": self.name,
            "avatar": self.avatar
        }


class Object(ABC):
    """
    Base class for all Ryver objects.

    :param ryver: The parent :py:class:`pyryver.pyryver.Ryver` instance.
    :param obj_type: The object's type, a constant beginning with ``TYPE_`` in :ref:`pyryver.util <util-data-constants>`.
    """

    def __init__(self, ryver: "Ryver", obj_type: str, data: dict):
        self._ryver = ryver
        self._data = data
        self._obj_type = obj_type
        self._entity_type = ENTITY_TYPES[obj_type]
        self._id = data["id"]

    def get_ryver(self) -> "Ryver":
        """
        Get the Ryver session this object was retrieved from.
        """
        return self._ryver

    def get_id(self) -> typing.Any:
        """
        Get the ID of this object.

        This is usually an integer, however for messages it is a string instead.
        """
        return self._id

    def get_type(self) -> str:
        """
        Get the type of this object.
        """
        return self._obj_type

    def get_entity_type(self) -> str:
        """
        Get the entity type of this object.
        """
        return self._entity_type

    def get_raw_data(self) -> dict:
        """
        Get the raw data of this object.

        The raw data is a dictionary directly obtained from parsing the JSON
        response.
        """
        return self._data


class Message(Object):
    """
    Any generic Ryver message, with an author, body, and reactions.
    """
    @abstractmethod
    def get_body(self) -> str:
        """
        Get the body of this message.
        """

    def get_creator(self) -> Creator:
        """
        Get the Creator of this message.

        Note that this is different from the author. Creators are used to
        override the display name and avatar of a user. If the username and 
        avatar were not overridden, this will return None.
        """
        if self._data["createSource"]:
            return Creator(self._data["createSource"]["displayName"], self._data["createSource"]["avatar"])
        else:
            return None

    @abstractmethod
    def get_author_id(self) -> int:
        """
        Get the ID of the author of this message.
        """

    async def get_author(self) -> "User":
        """
        Get the author of this message, as a :py:class:`User` object.

        This method sends requests.
        """
        return await self._ryver.get_object(TYPE_USER, self.get_author_id())

    async def react(self, emoji: str) -> None:
        """
        React to a message with an emoji. 

        This method sends requests.

        :param emoji: The string name of the reacji (e.g. "thumbsup").
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/React(reaction='{emoji}')"
        await self._ryver._session.post(url)

    def get_reactions(self) -> dict:
        """
        Get the reactions on this message.

        Returns a dict of {emoji: [users]}.
        """
        return self._data['__reactions']

    def get_reaction_counts(self) -> dict:
        """
        Count the number of reactions for each emoji on a message.

        Returns a dict of {emoji: number_of_reacts}.
        """
        reactions = self.get_reactions()
        counts = {reaction: len(users)
                  for reaction, users in reactions.items()}
        return counts

    def get_attached_file(self) -> "File":
        """
        Get the file attached to this message, if there is one.

        Note that files obtained from this only have a limited amount of information,
        including the ID, name, URL, size and type. Attempting to get any other info
        will result in a KeyError. To obtain the full file info, use :py:meth:`Ryver.get_object()`
        with `TYPE_FILE <pyryver.util.TYPE_FILE>` and the ID.

        Returns None otherwise.
        """
        if "extras" in self._data and "file" in self._data["extras"]:
            return File(self._ryver, TYPE_FILE, self._data["extras"]["file"])
        else:
            return None


class TopicReply(Message):
    """
    A reply on a topic.
    """

    def get_body(self) -> str:
        """
        Get the body of this message.
        """
        return self._data["comment"]

    def get_author(self) -> "User":
        """
        Get the author of this reply, as a :py:class:`User` object.

        Unlike the other implementations, this does not send any requests.
        """
        return User(self._ryver, TYPE_USER, self._data["createUser"])

    def get_author_id(self) -> int:
        """
        Get the ID of the author of this reply.
        """
        return self._data["createUser"]["id"]

    def get_topic(self) -> "Topic":
        """
        Get the topic this reply was sent to.
        """
        return Topic(self._ryver, TYPE_TOPIC, self._data["post"])


class Topic(Message):
    """
    A Ryver topic in a chat.
    """

    def get_subject(self) -> str:
        """
        Get the subject of this topic.
        """
        return self._data["subject"]

    def get_body(self) -> str:
        """
        Get the body of this topic.
        """
        return self._data["body"]

    def get_author_id(self) -> int:
        """
        Get the ID of the author of this topic.
        """
        return self._data["createUser"]["id"]

    async def reply(self, message: str, creator: Creator = None) -> TopicReply:
        """
        Reply to the topic.

        This method sends requests.

        For unknown reasons, overriding the creator does not work for this method.

        :param message: The reply content
        """
        url = self._ryver._url_prefix + TYPE_TOPIC_REPLY + "?$format=json"
        data = {
            "comment": message,
            "post": {
                "id": self.get_id()
            }
        }
        if creator:
            data["createSource"] = creator.to_dict()
        async with self._ryver._session.post(url, json=data) as resp:
            return TopicReply(self._ryver, TYPE_TOPIC_REPLY, (await resp.json())["d"]["results"])

    async def get_replies(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator[TopicReply]:
        """
        Get all the replies to this topic.

        This method sends requests.

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results.
        """
        url = self._ryver._url_prefix + TYPE_TOPIC_REPLY + \
            f"?$format=json&$filter=((post/id eq {self.get_id()}))&$expand=createUser,post"
        async for reply in get_all(session=self._ryver._session, url=url, top=top, skip=skip, param_sep="&"):
            yield TopicReply(self._ryver, TYPE_TOPIC_REPLY, reply)


class ChatMessage(Message):
    """
    A Ryver chat message.
    """

    def get_body(self) -> str:
        """
        Get the message body.
        """
        return self._data["body"]

    def get_author_id(self) -> int:
        """
        Get the ID of the author of this message.
        """
        return self._data["from"]["id"]

    def get_chat_type(self) -> str:
        """
        Gets the type of chat that this message was sent to, as a string.

        This string will be one of the ENTITY_TYPES values
        """
        return self._data["to"]["__metadata"]["type"]

    def get_chat_id(self) -> int:
        """
        Get the id of the chat that this message was sent to, as an integer.

        Note that this is different from :py:meth:`get_chat()` as the id is stored in
        the message data and is good for most API purposes while ``get_chat()``
        returns an entire Chat object, which might not be necessary depending
        on what you're trying to do.
        """
        return self._data["to"]["id"]

    async def get_chat(self) -> "Chat":
        """
        Get the chat that this message was sent to, as a :py:class:`Chat` object.

        This method sends requests.
        """
        return await self._ryver.get_object(get_type_from_entity(self.get_chat_type()), self.get_chat_id())

    # Override Message.react() because a different URL is used
    async def react(self, emoji: str) -> None:
        """
        React to a message with an emoji. 

        This method sends requests.

        :param emoji: The string name of the reacji (e.g. "thumbsup").
        """
        url = self._ryver._url_prefix + \
            f"{get_type_from_entity(self.get_chat_type())}({self.get_chat_id()})/Chat.React()"
        data = {
            "id": self.get_id(),
            "reaction": emoji
        }
        await self._ryver._session.post(url, json=data)

    async def delete(self) -> None:
        """
        Deletes the message.
        """
        url = self._ryver._url_prefix + \
            f"{get_type_from_entity(self.get_chat_type())}({self.get_chat_id()})/Chat.DeleteMessage()?$format=json"
        data = {
            "id": self.get_id(),
        }
        await self._ryver._session.post(url, json=data)
    
    async def edit(self, body: str, creator: Creator = None) -> None:
        """
        Edit the message.

        :param body: The new message content.
        :param creator: The new message creator; optional, if unset left as-is.
        """
        url = self._ryver._url_prefix + \
            f"{get_type_from_entity(self.get_chat_type())}({self.get_chat_id()})/Chat.UpdateMessage()?$format=json"
        data = {
            "id": self.get_id(),
            "body": body,
        }
        if creator:
            data["createSource"] = creator.to_dict()
        await self._ryver._session.post(url, json=data)


class Chat(Object):
    """
    Any Ryver chat you can send messages to.

    E.g. Teams, forums, user DMs, etc.
    """

    def get_jid(self) -> str:
        """
        Get the JID (JabberID) of this chat.

        The JID is used in the websockets interface.
        """
        return self._data["jid"]
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this chat.
        """

    async def send_message(self, message: str, creator: Creator = None) -> str:
        """
        Send a message to this chat.

        Specify a creator to override the username and profile of the message creator.

        This method sends requests.

        Returns the ID of the chat message sent. Note that message IDs are
        strings.

        :param message: The message contents.
        :param creator: The overriden creator; optional, if unset uses the logged-in user's profile.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/Chat.PostMessage()"
        data = {
            "body": message
        }
        if creator:
            data["createSource"] = creator.to_dict()
        async with self._ryver._session.post(url, json=data) as resp:
            return (await resp.json())["d"]["id"]

    async def create_topic(self, subject: str, body: str, creator: Creator = None) -> Topic:
        """
        Create a topic in this chat.

        This method sends requests.

        Returns the topic created.

        :param subject: The subject (or title) of the new topic.
        :param body: The contents of the new topic.
        :param creator: The overriden creator; optional, if unset uses the logged-in user's profile.
        """
        url = self._ryver._url_prefix + "posts"
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
            "recordType": "note"
        }
        if creator:
            data["createSource"] = creator.to_dict()
        async with self._ryver._session.post(url, json=data) as resp:
            return Topic(self._ryver, TYPE_TOPIC, (await resp.json())["d"]["results"])

    async def get_topics(self, archived: bool = False, top: int = -1, skip: int = 0) -> typing.AsyncIterator[Topic]:
        """
        Get all the topics in this chat.

        This method sends requests.

        :param archived: If True, only include archived topics in the results, otherwise, only include non-archived topics.
        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
        async for topic in get_all(session=self._ryver._session, url=url, param_sep="&", top=top, skip=skip):
            yield Topic(self._ryver, TYPE_TOPIC, topic)

    async def get_messages(self, count: int) -> typing.List[ChatMessage]:
        """
        Get a number of messages (most recent first) in this chat.

        This method sends requests.

        :param count: Maximum number of results.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/Chat.History()?$format=json&$top={count}"
        async with self._ryver._session.get(url) as resp:
            messages = (await resp.json())["d"]["results"]
        return [ChatMessage(self._ryver, TYPE_MESSAGE, data) for data in messages]

    async def get_message_from_id(self, id: str, before: int = 0, after: int = 0) -> typing.List[Message]:
        """
        Get a message from an ID, optionally also messages before and after it too.

        .. warning:: 
           Before and after cannot exceed 25 messages, otherwise an HTTPError will be raised
           with the error code 400 Bad Request.

        This method sends requests.

        This method does not support top/skip.

        :param id: The ID of the message to retrieve, and the reference point for the ``before`` and ``after`` parameters.
        :param before: How many extra messages to retrieve before the specified one.
        :param after: How many extra messages to retrieve after the specified one.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/Chat.History.Message(id='{id}',before={before},after={after})?$format=json"
        async with self._ryver._session.get(url) as resp:
            messages = (await resp.json())["d"]["results"]
        return [ChatMessage(self._ryver, TYPE_MESSAGE, data) for data in messages]


class User(Chat):
    """
    A Ryver user.
    """

    ROLE_USER = "ROLE_USER"
    ROLE_ADMIN = "ROLE_ADMIN"
    ROLE_GUEST = "ROLE_GUEST"

    def get_username(self) -> str:
        """
        Get the username of this user.
        """
        return self._data["username"]

    def get_display_name(self) -> str:
        """
        Get the display name of this user.
        """
        return self._data["displayName"]
    
    def get_name(self) -> str:
        """
        Get the display name of this user.
        """
        return self._data["displayName"]

    def get_role(self) -> str:
        """
        Get this user's role in their profile.

        .. note:: 
           This is different from :py:meth:`get_roles()`. While this one gets the "Role"
           of the user from the profile, ``get_roles()`` gets the user's roles in the
           organization (user, guest, admin).

        """
        return self._data["description"]

    def get_about(self) -> str:
        """
        Get this user's About.
        """
        return self._data["aboutMe"]

    def get_time_zone(self) -> str:
        """
        Get this user's Time Zone.
        """
        return self._data["timeZone"]

    def get_email_address(self) -> str:
        """
        Get this user's Email Address.
        """
        return self._data["emailAddress"]

    def get_activated(self) -> bool:
        """
        Get whether this user's account is activated.
        """
        return self._data["active"]

    def get_roles(self) -> typing.List[str]:
        """
        Get this user's role in the organization.

        .. note:: 
           This is different from :py:meth:`get_role()`. While this one gets the user's
           roles in the organization (user, guest, admin), ``get_role()`` gets the
           user's role from their profile.

        """
        return self._data["roles"]

    def is_admin(self) -> bool:
        """
        Get whether this user is an org admin.
        """
        return User.ROLE_ADMIN in self.get_roles()

    async def set_profile(self, display_name: str = None, role: str = None, about: str = None) -> None:
        """
        Update this user's profile.

        If any of the arguments are None, they will not be changed.

        This method sends requests.

        .. note::
           This also updates these properties in this object.

        :param display_name: The user's new display_name.
        :param role: The user's new role, as described in :py:meth:`get_role()`.
        :param about: The user's new "about me" blurb.
        """
        url = self._ryver._url_prefix + \
            f"/{self.get_type()}(id={self.get_id()})"
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

        This method sends requests.

        .. note::
           This also updates these properties in this object.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/User.Active.Set(value='{'true' if activated else 'false'}')"
        await self._ryver._session.post(url)
        self._data["active"] = activated

    async def set_org_role(self, role: str) -> None:
        """
        Set a user's role in this organization, as described in :py:meth:`get_roles()`.

        This can be either ROLE_USER, ROLE_ADMIN or ROLE_GUEST.

        This method sends requests.

        .. note::
           This also updates these properties in this object.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/User.Role.Set(role='{role}')"
        await self._ryver._session.post(url)

        self._data["roles"] = [role]
        # Admins also have the normal user role
        if role == User.ROLE_ADMIN:
            self._data["roles"].append(User.ROLE_USER)

    async def create_topic(self, from_user: "User", subject: str, body: str, creator: Creator = None) -> Topic:
        """
        Create a topic in this user's DMs.

        This method sends requests.

        Returns the topic created.

        :param from_user: The user that will create the topic; must be the same as the logged-in user.
        :param subject: The subject (or title) of the created topic.
        :param body: The contents of the created topic.
        """
        url = self._ryver._url_prefix + "posts"
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
                        "inType": from_user.entity_type,
                        "inId": from_user.id,
                        "inName": from_user.get_display_name(),
                    }
                ]
            },
            "recordType": "note"
        }
        if creator:
            data["createSource"] = creator.to_dict()
        async with self._ryver._session.post(url, json=data) as resp:
            return Topic(self._ryver, TYPE_TOPIC, (await resp.json())["d"]["results"])


class GroupChatMember(Object):
    """
    A member in a forum or team.
    """

    ROLE_MEMBER = "ROLE_TEAM_MEMBER"
    ROLE_ADMIN = "ROLE_TEAM_ADMIN"

    def get_role(self) -> str:
        """
        Get the role of this member.
        """
        return self._data["role"]

    def get_user(self) -> User:
        """
        Get this member as a :py:class:`User` object.
        """
        return User(self._ryver, TYPE_USER, self._data["member"])

    def is_admin(self) -> bool:
        """
        Get whether this member is an admin of their forum.

        .. warning::
           This method does not check for org admins.

        """
        return GroupChatMember.ROLE_ADMIN == self.get_role()


class GroupChat(Chat):
    """
    A Ryver team or forum.
    """

    def get_name(self) -> str:
        """
        Get the name of this chat.
        """
        return self._data["name"]

    def get_nickname(self) -> str:
        """
        Get the nickname of this chat.
        """
        return self._data["nickname"]

    async def get_members(self, top: int = -1, skip: int = 0) -> typing.AsyncIterator[GroupChatMember]:
        """
        Get all the members of this chat.

        This method sends requests.

        :param top: Maximum number of results; optional, if unspecified return all results.
        :param skip: Skip this many results.
        """
        url = self._ryver._url_prefix + \
            f"/{self.get_type()}({self.get_id()})/members?$expand=member"
        async for member in get_all(session=self._ryver._session, url=url, top=top, skip=skip, param_sep="&"):
            yield GroupChatMember(self._ryver, TYPE_GROUPCHAT_MEMBER, member)

    async def get_member(self, id: int) -> GroupChatMember:
        """
        Get a member by user ID.

        This method sends requests.

        If the user is not found, this method will return None.
        """
        url = self._ryver._url_prefix + \
            f"/{self.get_type()}({self.get_id()})/members?$expand=member&$filter=((member/id eq {id}))"
        async with self._ryver._session.get(url) as resp:
            member = (await resp.json())["d"]["results"]
        return GroupChatMember(self._ryver, TYPE_GROUPCHAT_MEMBER, member[0]) if member else None


class Forum(GroupChat):
    """
    A Ryver forum.
    """


class Team(GroupChat):
    """
    A Ryver team.
    """


class Notification(Object):
    """
    A Ryver user notification.
    """

    PREDICATE_MENTION = "chat_mention"
    PREDICATE_GROUP_MENTION = "group_mention"
    PREDICATE_COMMENT = "commented_on"
    PREDICATE_TASK_COMPLETED = "completed"

    def get_predicate(self) -> str:
        """
        Get the "predicate", or type, of this notification.

        E.g.
          - chat_mention - User was @mentioned
          - group_mention - User was mentioned through @team or @here
          - commented_on - A topic was commented on
          - completed - A task was completed
        """
        return self._data["predicate"]

    def get_subject_entity_type(self) -> str:
        """
        Get the entity type of the "subject" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        user that did the action which caused this notification.
        """
        return self._data["subjectType"]

    def get_subject_id(self) -> int:
        """
        Get the ID of the "subject" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        user that did the action which caused this notification.
        """
        return self._data["subjectId"]

    def get_subjects(self) -> typing.List[dict]:
        """
        Get the "subjects" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        user that did the action which caused this notification. It is also 
        unknown why this is an array, as it seems to only ever contain one
        element.
        """
        return self._data["subjects"]

    def get_object_entity_type(self) -> str:
        """
        Get entity type of the "object" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        target of an @mention for mentions, the topic for topic comments, or the
        task for task activities.
        """
        return self._data["objectType"]

    def get_object_id(self) -> int:
        """
        Get the ID of the "object" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        target of an @mention for mentions, the topic for topic comments, or the
        task for task activities.
        """
        return self._data["objectId"]

    def get_object(self) -> dict:
        """
        Get the "object" of this notification.

        The exact nature of this field is not yet known, but it seems to be the
        target of an @mention for mentions, the topic for topic comments, or the
        task for task activities.
        """
        return self._data["object"]

    def get_via_entity_type(self) -> str:
        """
        Get the entity type of the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. For task completions, there is NO via.
        """
        return self._data["viaType"]

    def get_via_id(self) -> int:
        """
        Get the ID of the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. For task completions, there is NO via.
        """
        return self._data["viaId"]

    def get_via(self) -> dict:
        """
        Get the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. For task completions, there is NO via.
        """
        return self._data["via"]

    def get_new(self) -> bool:
        """
        Get whether this notification is new.
        """
        return self._data["new"]

    def get_unread(self) -> bool:
        """
        Get whether this notification is unread.
        """
        return self._data["unread"]

    async def set_status(self, unread: bool, new: bool) -> None:
        """
        Set the read/unread and seen/unseen (new) status of this notification.

        This method sends requests.

        .. note:: 
           This also updates these properties in this object.

        """
        data = {
            "unread": unread,
            "new": new,
        }
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})?$format=json"
        await self._ryver._session.patch(url, json=data)
        self._data["unread"] = unread
        self._data["new"] = new


class File(Object):
    """
    An uploaded file.

    This class also contains constants for some common MIME types.
    """

    def get_title(self) -> str:
        """
        Get the title of this file.
        """
        return self._data["title"]

    def get_name(self) -> str:
        """
        Get the name of this file.
        """
        return self._data["fileName"]

    def get_size(self) -> int:
        """
        Get the size of this file in bytes.
        """
        return self._data["fileSize"]

    def get_url(self) -> str:
        """
        Get the URL of this file.
        """
        return self._data["url"]

    def get_MIME_type(self) -> str:
        """
        Get the MIME type of this file.
        """
        return self._data.get("type", self._data.get("fileType", None))
    
    def request_data(self) -> aiohttp.ClientResponse:
        """
        Get the file data.

        Returns an aiohttp request response to the file URL.
        """
        # Use aiohttp.request directly because we don't want to send the auth header
        # Otherwise we'll get a 400
        return aiohttp.request("GET", self.get_url())
    
    async def download_data(self) -> bytes:
        """
        Download the file data.

        This method sends requests.
        """
        async with aiohttp.request("GET", self.get_url()) as resp:
            resp.raise_for_status()
            return await resp.content.read()

    async def delete(self) -> None:
        """
        Delete this file.

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})?$format=json"
        await self._ryver._session.delete(url)


class Storage(Object):
    """
    Generic storage, e.g. uploaded files.

    Note that while storage objects contain files, the File class does not
    inherit from this class.
    """

    def get_file(self) -> File:
        """
        Get the file stored.
        """
        return File(self._ryver, TYPE_FILE, self._data["file"])


TYPES_DICT = {
    TYPE_USER: User,
    TYPE_FORUM: Forum,
    TYPE_TEAM: Team,
    TYPE_TOPIC: Topic,
    TYPE_MESSAGE: ChatMessage,
    TYPE_TOPIC_REPLY: TopicReply,
    TYPE_NOTIFICATION: Notification,
    TYPE_GROUPCHAT_MEMBER: GroupChatMember,
    TYPE_FILE: File,
    TYPE_STORAGE: Storage,
}


def get_obj_by_field(objs: typing.List[Object], field: str, value: typing.Any) -> Object:
    """
    Gets an object from a list of objects by a field.

    For example, this function can find a chat with a specific nickname in a
    list of chats.

    :param objs: List of objects to search in.
    :param field: The field's name (usually a constant beginning with ``FIELD_`` in :ref:`pyryver.util <util-data-constants>`) within the object's JSON data.
    :param value: The value to look for.
    """
    for obj in objs:
        if obj._data[field] == value:
            return obj
    return None

from pyryver.ryver import *

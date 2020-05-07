"""
A simple Python library for Ryver's REST APIs.
"""

import aiohttp
import asyncio
import typing
import os
import json
from abc import ABC, abstractmethod
from base64 import b64encode
from getpass import getpass


class Creator:
    """
    A message creator, with a name and an avatar.

    This can be used to override the sender's display name and avatar.
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
    """

    def __init__(self, ryver, obj_type: str, data: dict):
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
        Get the author of this message, as a User object.

        This method sends requests.
        """
        return await self._ryver.get_object(TYPE_USER, self.get_author_id())

    async def react(self, emoji: str) -> None:
        """
        React to this message with an emoji, specified with the string name (e.g. "thumbsup").

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/React(reaction='{emoji}')"
        async with self._ryver._session.post(url) as resp:
            pass

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
        will result in a KeyError. To obtain the full file info, use Ryver.get_object()
        with TYPE_FILE and the ID.

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
        Get the author of this reply, as a User object.

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

    async def get_replies(self, top: int = -1, skip: int = 0) -> typing.List[TopicReply]:
        """
        Get all the replies to this topic.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        This method sends requests.
        """
        url = self._ryver._url_prefix + TYPE_TOPIC_REPLY + \
            f"?$format=json&$filter=((post/id eq {self.get_id()}))&$expand=createUser,post"
        replies = await _get_all(session=self._ryver._session, url=url, top=top,
                                 skip=skip, param_sep="&")
        return [TopicReply(self._ryver, TYPE_TOPIC_REPLY, data) for data in replies]


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

        Note that this is different from get_chat() as the id is stored in
        the message data and is good for most API purposes while get_chat()
        returns an entire Chat object, which might not be necessary depending
        on what you're trying to do.
        """
        return self._data["to"]["id"]

    async def get_chat(self) -> "Chat":
        """
        Get the chat that this message was sent to, as a Chat object.

        This method sends requests.
        """
        return await self._ryver.get_object(_get_type_from_entity(self.get_chat_type()), self.get_chat_id())

    # Override Message.react() because a different URL is used
    async def react(self, emoji: str) -> None:
        """
        React to a message with an emoji, specified with the string name (e.g. "thumbsup").

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"{_get_type_from_entity(self.get_chat_type())}({self.get_chat_id()})/Chat.React()"
        data = {
            "id": self.get_id(),
            "reaction": emoji
        }
        async with self._ryver._session.post(url, json=data) as resp:
            pass

    async def delete(self) -> None:
        """
        Deletes the message.
        """
        url = self._ryver._url_prefix + \
            f"{_get_type_from_entity(self.get_chat_type())}({self.get_chat_id()})/Chat.DeleteMessage()?$format=json"
        data = {
            "id": self.get_id(),
        }
        async with self._ryver._session.post(url, json=data) as resp:
            pass


class Chat(Object):
    """
    A Ryver chat (forum, team, user, etc).
    """

    async def send_message(self, message: str, creator: Creator = None) -> str:
        """
        Send a message to this chat.

        Specify a creator to override the username and profile of the message creator.

        This method sends requests.

        Returns the ID of the chat message sent. Note that message IDs are
        strings.
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

    async def get_topics(self, archived: bool = False, top: int = -1, skip: int = 0) -> typing.List[Topic]:
        """
        Get all the topics in this chat.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
        topics = await _get_all(session=self._ryver._session, url=url,
                                param_sep="&", top=top, skip=skip)
        return [Topic(self._ryver, TYPE_TOPIC, data) for data in topics]

    async def get_messages(self, count: int) -> typing.List[ChatMessage]:
        """
        Get a number of messages (most recent first) in this chat.

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/Chat.History()?$format=json&$top={count}"
        async with self._ryver._session.get(url) as resp:
            messages = (await resp.json())["d"]["results"]
        return [ChatMessage(self._ryver, TYPE_MESSAGE, data) for data in messages]

    async def get_message_from_id(self, id: str, before: int = 0, after: int = 0) -> typing.List[Message]:
        """
        Get a message from an ID, optionally also messages before and after it too.

        Note: Before and after cannot exceed 25 messages, otherwise an HTTPError will be raised
        with the error code 400 Bad Request.

        This method sends requests.

        This method does not support top/skip.
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

    def get_role(self) -> str:
        """
        Get this user's Role in their profile.

        Note this is different from get_roles(). While this one gets the "Role"
        of the user from the profile, get_roles() gets the user's roles in the
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

        Note this is different from get_role(). While this one gets the user's
        roles in the organization (user, guest, admin), get_role() gets the
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

        Note: This also updates these properties in this object!
        """
        url = self._ryver._url_prefix + \
            f"/{self.get_type()}(id={self.get_id()})"
        data = {
            "aboutMe": about if about is not None else self.get_about(),
            "description": role if role is not None else self.get_role(),
            "displayName": display_name if display_name is not None else self.get_display_name(),
        }
        async with self._ryver._session.patch(url, json=data) as resp:
            pass

        self._data["aboutMe"] = data["aboutMe"]
        self._data["description"] = data["description"]
        self._data["displayName"] = data["displayName"]

    async def set_activated(self, activated: bool) -> None:
        """
        Activate or deactivate the user. Requires admin.

        This method sends requests.

        Note: This also updates these properties in this object!
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/User.Active.Set(value='{'true' if activated else 'false'}')"
        async with self._ryver._session.post(url) as resp:
            pass
        self._data["active"] = activated

    async def set_org_role(self, role: str) -> None:
        """
        Set a user's role in this organization.

        This can be either ROLE_USER, ROLE_ADMIN or ROLE_GUEST.

        This method sends requests.

        Note: This also updates these properties in this object!
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})/User.Role.Set(role='{role}')"
        async with self._ryver._session.post(url) as resp:
            pass

        self._data["roles"] = [role]
        # Admins also have the normal user role
        if role == User.ROLE_ADMIN:
            self._data["roles"].append(User.ROLE_USER)

    async def create_topic(self, from_user: "User", subject: str, body: str, creator: Creator = None) -> Topic:
        """
        Create a topic in this chat.

        from_user must be the User object of the same user as in the Ryver
        object. E.g. if the Ryver object was created with a username of foo,
        from_user must be the User object of the user. (Don't blame me the API
        is weird.)

        This method sends requests.

        Returns the topic created.
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
        Get this member as a User object.
        """
        return User(self._ryver, TYPE_USER, self._data["member"])

    def is_admin(self) -> bool:
        """
        Get whether this member is an admin of their forum.

        Note that this does not check for org admins.
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

    async def get_members(self, top: int = -1, skip: int = 0) -> typing.List[GroupChatMember]:
        """
        Get all the members of this chat.

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"/{self.get_type()}({self.get_id()})/members?$expand=member"
        members = await _get_all(session=self._ryver._session, url=url,
                                 top=top, skip=skip, param_sep="&")
        return [GroupChatMember(self._ryver, TYPE_GROUPCHAT_MEMBER, data) for data in members]

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
        etc. Note that for task completions, there is NO via.
        """
        return self._data["viaType"]

    def get_via_id(self) -> int:
        """
        Get the ID of the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. Note that for task completions, there is NO via.
        """
        return self._data["viaId"]

    def get_via(self) -> dict:
        """
        Get the "via" of this notification.

        The exact nature of this field is not yet known, but it seems to
        contain information about whatever caused this notification. For
        example, the chat message of an @mention, the topic reply for a reply,
        etc. Note that for task completions, there is NO via.
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

        Note: This also updates these properties in this object!
        """
        data = {
            "unread": unread,
            "new": new,
        }
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})?$format=json"
        async with self._ryver._session.patch(url, json=data) as resp:
            pass
        self._data["unread"] = unread
        self._data["new"] = new


class File(Object):
    """
    An uploaded file.

    This class also contains constants for some common MIME types.
    """

    MIME_TYPE_TEXT = "text/plain"
    MIME_TYPE_HTML = "text/html"
    MIME_TYPE_CSS = "text/css"
    MIME_TYPE_CSV = "text/csv"
    MIME_TYPE_JAVASCRIPt = "text/javascript"
    MIME_TYPE_XML = "text/xml"
    MIME_TYPE_JSON = "application/json"
    MIME_TYPE_BMP = "image/bmp"
    MIME_TYPE_PNG = "image/png"
    MIME_TYPE_GIF = "image/gif"
    MIME_TYPE_JPEG = "image/jpeg"
    MIME_TYPE_SVG = "image/svg+xml"
    MIME_TYPE_TIFF = "image/tiff"
    MIME_TYPE_PDF = "application/pdf"
    MIME_TYPE_JAR = "application/java-archive"
    MIME_TYPE_ZIP = "application/zip"
    MIME_TYPE_7Z = "application/x-7z-compressed"
    MIME_TYPE_GZ = "application/gzip"
    MIME_TYPE_TAR = "application/x-tar"
    MIME_TYPE_RTF = "application/rtf"
    MIME_TYPE_DOC = "application/msword"
    MIME_TYPE_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    MIME_TYPE_PPT = "application/vnd.ms-powerpoint"
    MIME_TYPE_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    MIME_TYPE_XLS = "application/vnd.ms-excel"
    MIME_TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    MIME_TYPE_BINARY = "application/octet-stream"

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
        return self._data.get("type", self._data["fileType"])

    async def delete(self) -> None:
        """
        Delete this file.

        This method sends requests.
        """
        url = self._ryver._url_prefix + \
            f"{self.get_type()}({self.get_id()})?$format=json"
        async with self._ryver._session.delete(url) as resp:
            pass


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


class Ryver:
    """
    A Ryver session contains login credentials and organization information.

    This is the starting point for any application using pyryver.

    If the organization or username is not provided, it will be prompted using
    input(). If the password is not provided, it will be prompted using 
    getpass().
    """

    def __init__(self, org: str = None, user: str = None, password: str = None):
        if not org:
            org = input("Organization: ")
        if not user:
            user = input("Username: ")
        if not password:
            password = getpass()

        self._url_prefix = "https://" + org + ".ryver.com/api/1/odata.svc/"
        self._session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(user, password), raise_for_status=True)

    async def __aenter__(self):
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc, *exc_info):
        return await self._session.__aexit__(exc, *exc_info)

    async def close(self):
        """
        Close this session.
        """
        await self._session.close()

    async def get_object(self, obj_type: str, obj_id: int) -> Object:
        """
        Get an object from Ryver with a type and ID.

        This method sends requests.
        """
        url = self._url_prefix + f"{obj_type}({obj_id})"
        async with self._session.get(url) as resp:
            return TYPES_DICT[obj_type](self, obj_type, (await resp.json())["d"]["results"])

    async def get_chats(self, obj_type: str, top: int = -1, skip: int = 0) -> typing.List[Chat]:
        """
        Get a list of chats (teams, forums, users, etc) from Ryver.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        This method sends requests.
        Consider using get_cached_chats() to cache the data in a JSON file.
        """
        url = self._url_prefix + obj_type
        chats = await _get_all(session=self._session, url=url, top=top, skip=skip)
        return [TYPES_DICT[obj_type](self, obj_type, chat) for chat in chats]

    async def get_cached_chats(self, obj_type: str, force_update: bool = False, name: str = None, top: int = -1, skip: int = 0) -> typing.List[Chat]:
        """
        Attempt to load a list of chats (teams, forums, users, etc) from JSON,
        and if not found, get them from Ryver.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip. (These arguments are not respected if reading
        from a JSON file.)

        This method only performs new requests if the JSON file specified by
        name is not found. You can also force it to perform a request to update
        the lists by setting force_update to True.
        """
        name = name or "pyryver." + obj_type + ".json"
        if not force_update and os.path.exists(name):
            with open(name, "r") as f:
                data = json.load(f)
                return [TYPES_DICT[obj_type](self, obj_type, chat) for chat in data]
        else:
            chats = await self.get_chats(obj_type, top=top, skip=skip)
            with open(name, "w") as f:
                json.dump([chat._data for chat in chats], f)
            return chats

    async def get_notifs(self, unread: bool = False, top: int = -1, skip: int = 0) -> typing.List[Notification]:
        """
        Get all the user's notifications. 

        If unread is true, only unread notifications will be retrieved.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        This method sends requests.
        """
        url = self._url_prefix + TYPE_NOTIFICATION + \
            "?$format=json&$orderby=modifyDate desc"
        if unread:
            url += "&$filter=((unread eq true))"
        notifs = await _get_all(session=self._session, url=url, top=top, skip=skip, param_sep="&")
        return [Notification(self, TYPE_NOTIFICATION, data) for data in notifs]

    async def mark_all_notifs_read(self) -> int:
        """
        Marks all the user's notifications as read.

        This method sends requests.

        Returns how many notifications were marked as read.
        """
        url = self._url_prefix + TYPE_NOTIFICATION + \
            "/UserNotification.MarkAllRead()?$format=json"
        async with self._session.post(url) as resp:
            return (await resp.json())["d"]["count"]

    async def mark_all_notifs_seen(self) -> int:
        """
        Marks all the user's notifications as seen.

        This method sends requests.

        Returns how many notifications were marked as seen.
        """
        url = self._url_prefix + TYPE_NOTIFICATION + \
            "/UserNotification.MarkAllSeen()?$format=json"
        async with self._session.post(url) as resp:
            return (await resp.json())["d"]["count"]

    async def upload_file(self, filename: str, filedata: typing.Any, filetype: str = None) -> Storage:
        """
        Upload a file to Ryver.

        Although this method uploads a file, the returned object is an instance of Storage.
        Use Storage.get_file() to obtain the actual File object.

        Note that this method does send requests, so it may take some time,
        depending on file size.
        """
        url = self._url_prefix + TYPE_STORAGE + \
            "/Storage.File.Create(createFile=true)?$expand=file&$format=json"
        data = aiohttp.FormData()
        data.add_field("file", filedata, filename=filename,
                       content_type=filetype)
        async with self._session.post(url, data=data) as resp:
            return Storage(self, TYPE_STORAGE, await resp.json())


TYPE_USER = "users"
TYPE_FORUM = "forums"
TYPE_TEAM = "workrooms"
TYPE_TOPIC = "posts"
TYPE_TOPIC_REPLY = "postComments"
TYPE_NOTIFICATION = "userNotifications"
TYPE_GROUPCHAT_MEMBER = "workroomMembers"
TYPE_FILE = "files"
TYPE_STORAGE = "storage"

# Note: messages aren't really a "real" type in the Ryver API
# They're just here for the sake of completeness and to fit in with the rest of pyryver
TYPE_MESSAGE = "messages"

ENTITY_TYPES = {
    TYPE_USER: "Entity.User",
    TYPE_FORUM: "Entity.Forum",
    TYPE_TEAM: "Entity.Workroom",
    TYPE_TOPIC: "Entity.Post",
    TYPE_MESSAGE: "Entity.ChatMessage",
    TYPE_TOPIC_REPLY: "Entity.Post.Comment",
    TYPE_NOTIFICATION: "Entity.UserNotification",
    TYPE_GROUPCHAT_MEMBER: "Entity.Workroom.Member",
    TYPE_FILE: "Entity.File",
    TYPE_STORAGE: "Entity.Storage",
}

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

# Field names for get_obj_by_field
FIELD_USERNAME = "username"
FIELD_EMAIL_ADDR = "emailAddress"
FIELD_DISPLAY_NAME = "displayName"
FIELD_NAME = "name"
FIELD_NICKNAME = "nickname"
FIELD_ID = "id"

# Here only for backwards compatibility, use the field names above
FIELD_USER_USERNAME = "username"
FIELD_USER_EMAIL_ADDR = "emailAddress"
FIELD_USER_DISPLAY_NAME = "displayName"
# Notification predicates
# Here only for backwards compatibility, use the ones in the notification class
NOTIF_PREDICATE_MENTION = "chat_mention"
NOTIF_PREDICATE_GROUP_MENTION = "group_mention"
NOTIF_PREDICATE_COMMENT = "commented_on"
NOTIF_PREDICATE_TASK_COMPLETED = "completed"


def get_obj_by_field(objs: typing.List[Object], field: str, value: typing.Any) -> Object:
    """
    Gets an object from a list of objects by a field.

    For example, this function can find a chat with a specific nickname in a
    list of chats.
    """
    for obj in objs:
        if obj._data[field] == value:
            return obj
    return None


async def _get_all(session: aiohttp.ClientSession, url: str, top: int = -1, skip: int = 0, param_sep: str = "?") -> typing.List[dict]:
    """
    Because the REST API only gives 50 results at a time, this function is used
    to retrieve all objects.

    Intended for internal use only.
    """
    # -1 means everything
    if top == -1:
        top = float("inf")
    result = []
    while True:
        # Respect the max specified
        count = min(top, 50)
        top -= count

        request_url = url + f"{param_sep}$skip={skip}&$top={count}"
        async with session.get(request_url) as resp:
            page = (await resp.json())["d"]["results"]

        result.extend(page)
        if len(page) == 0 or top == 0:
            break
        skip += len(page)
    return result


def _get_type_from_entity(entity_type: str) -> str:
    """
    Gets the object type from the entity type.

    Note that it doesn't actually return a class, just the string.
    """
    for t, e in ENTITY_TYPES.items():
        if e == entity_type:
            return t

"""
A simple Python library for Ryver's REST APIs.
"""

import requests
from base64 import b64encode
from getpass import getpass
import typing
import os
import json

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

class Object:
    """
    Base class for all Ryver objects.
    """
    def __init__(self, cred, obj_type: str, data: dict):
        self.cred = cred
        self.data = data
        self.obj_type = obj_type
        self.entity_type = ENTITY_TYPES[obj_type]
        self.id = data["id"]
    
    def get_id(self) -> typing.Any:
        """
        Get the ID of this object.

        This is usually an integer, however for messages it is a string instead.
        """
        return self.id
    
    def get_type(self) -> str:
        """
        Get the type of this object.
        """
        return self.obj_type
    
    def get_raw_data(self) -> dict:
        """
        Get the raw data of this object.

        The raw data is a dictionary directly obtained from parsing the JSON
        response.
        """
        return self.data

class TopicReply(Object):
    """
    A reply on a topic.
    """
    def get_message(self) -> str:
        """
        Get the message of this reply.
        """
        return self.data["comment"]

    def get_author_id(self) -> int:
        """
        Get the ID of the author of this reply.
        """
        return self.data["createUser"]["id"]

    def get_author(self):
        """
        Get the author of this reply, as a User object.

        Note that this method does send requests, so it may take some time.
        """
        return self.cred.get_object(TYPE_USER, self.data["createUser"]["id"])

class Topic(Object):
    """
    A Ryver topic in a chat.
    """
    # TODO: Add function to get replies
    def get_subject(self) -> str:
        """
        Get the subject of this topic.
        """
        return self.data["subject"]
    
    def get_body(self) -> str:
        """
        Get the body of this topic.
        """
        return self.data["body"]

    def reply(self, message: str) -> TopicReply:
        """
        Reply to the topic.

        Note that this method does send requests, so it may take some time.

        For unknown reasons, overriding the creator does not work for this.
        """
        url = self.cred.url_prefix + TYPE_TOPIC_REPLY + "?$format=json"
        data = {
            "comment": message,
            "post": {
                "id": self.get_id()
            }
        }
        resp = requests.post(url, json=data, headers=self.cred.headers)
        resp.raise_for_status()
        return TopicReply(self.cred, TYPE_TOPIC_REPLY, resp.json()["d"]["results"])

class Message(Object):
    """
    A Ryver chat message.
    """
    def get_body(self) -> str:
        """
        Get the message body.
        """
        return self.data["body"]
    
    def get_creator(self) -> Creator:
        """
        Get the Creator of this message.

        Note that this is different from the author. Creators are used to
        override the display name and avatar of a user. If the username and 
        avatar were not overridden, this will return None.
        """
        if self.data["createSource"]:
            return Creator(self.data["createSource"]["displayName"], self.data["createSource"]["avatar"])
        else:
            return None
    
    def get_author_id(self) -> int:
        """
        Get the ID of the author of this message.
        """
        self.data["from"]["id"]

    def get_author(self):
        """
        Get the author of this message, as a User object.

        Note that this method does send requests, so it may take some time.
        """
        return self.cred.get_object(TYPE_USER, self.data["from"]["id"])

    def get_chat_type(self):
        """
        Gets the type of chat that this message was sent to, as a string.

        This string will be one of the ENTITY_TYPES values
        """
        return self.data["to"]["__metadata"]["type"]

    def get_chat_id(self) -> int:
        """
        Get the id of the chat that this message was sent to, as an integer.

        Note that this is different from get_chat() as the id is stored in
        the message data and is good for most API purposes while get_chat()
        returns an entire Chat object, which might not be necessary depending
        on what you're trying to do.
        """
        return self.data["to"]["id"]

    def get_chat(self):
        """
        Get the chat that this message was sent to, as a Chat object.

        Note that this method does send requests, so it may take some time.
        """
        return self.cred.get_object(get_type_from_entity(self.get_chat_type()), self.get_chat_id())

    def react(self, emoji: str):
        """
        React to a message with an emoji, specified with the string name (e.g. "thumbsup").
        """
        url = self.cred.url_prefix + \
            "{chat_type}({chat_id})/Chat.React()".format(chat_type=self.get_chat_type(),chat_id=self.get_chat_id())
        data = {
            "id": self.id,
            "reaction": emoji
        }

        resp = requests.post(url, json=data, headers=self.cred.headers)
        resp.raise_for_status()

    def get_reaction_counts(self) -> dict:
        """
        Count the number of reactions for each emoji on a message

        Returns a dict of {emoji: number_of_reacts}
        """
        reactions = self.data['__reactions']
        counts = {reaction: len(users) for reaction, users in reactions.items()}
        return counts

    def delete(self):
        """
        Deletes the message.
        """
        url = self.cred.url_prefix + \
            "{chat_type}({chat_id})/Chat.DeleteMessage()?%24format=json".format(chat_type=self.get_chat_type(),chat_id=self.get_chat_id())
        data = {
            "id": self.id,
        }

        resp = requests.post(url, json=data, headers=self.cred.headers)
        resp.raise_for_status()

class Chat(Object):
    """
    A Ryver chat (forum, team, user, etc).
    """
    def send_message(self, message: str, creator: Creator = None) -> str:
        """
        Send a message to this chat.

        Note that this method does send requests, so it may take some time.

        Returns the ID of the chat message sent. Note that message IDs are
        strings.
        """
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/Chat.PostMessage()"
        data = {
            "body": message
        }
        if creator:
            data["createSource"] = creator.to_dict()
        resp = requests.post(url, json=data, headers=self.cred.headers)
        resp.raise_for_status()
        return resp.json()["d"]["id"]
    
    def create_topic(self, subject: str, body: str, creator: Creator = None) -> Topic:
        """
        Create a topic in this chat.

        Note that this method does send requests, so it may take some time.

        Returns the topic created.
        """
        url = self.cred.url_prefix + "posts"
        data = {
            "body": body,
            "subject": subject,
            "outAssociations": {
                "results": [
                    {
                        "inSecured": True,
                        "inType": self.entity_type,
                        "inId": self.id
                    }
                ]
            },
            "recordType": "note"
        }
        if creator:
            data["createSource"] = creator.to_dict()
        resp = requests.post(url, json=data, headers=self.cred.headers)
        resp.raise_for_status()
        return Topic(self.cred, TYPE_TOPIC, resp.json()["d"]["results"])
    
    def get_topics(self, archived: bool = False, top: int = -1, skip: int = 0) -> typing.List[Topic]:
        """
        Get all the topics in this chat.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        Note that this method does send requests, so it may take some time.
        """
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
        topics = get_all(url, self.cred.headers, param="&$skip", top=top, skip=skip)
        return [Topic(self.cred, TYPE_TOPIC, data) for data in topics]
    
    def get_messages(self, count: int) -> typing.List[Message]:
        """
        Get a number of messages (most recent first) in this chat.

        Note that this method does send requests, so it may take some time.
        """
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/Chat.History()?$format=json&$top={count}"
        resp = requests.get(url, headers = self.cred.headers)
        resp.raise_for_status()
        messages = resp.json()["d"]["results"]
        return [Message(self.cred, TYPE_MESSAGE, data) for data in messages]

class User(Chat):
    """
    A Ryver user.
    """
    def get_username(self) -> str:
        """
        Get the username of this user.
        """
        return self.data["username"]
    
    def get_display_name(self) -> str:
        """
        Get the display name of this user.
        """
        return self.data["displayName"]

    def set_activated(self, activated: bool) -> None:
        """
        Activate or deactivate the user. Requires admin.

        Note that this method does send requests, so it may take some time.
        """
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/User.Active.Set(value='{'true' if activated else 'false'}')"
        resp = requests.post(url, headers=self.cred.headers)
        resp.raise_for_status()

class Forum(Chat):
    """
    A Ryver forum.
    """
    def get_name(self) -> str:
        """
        Get the name of this forum.
        """
        return self.data["name"]
    
    def get_nickname(self) -> str:
        """
        Get the nickname of this forum.
        """
        return self.data["nickname"]

class Team(Chat):
    """
    A Ryver team.
    """
    def get_name(self) -> str:
        """
        Get the name of this team.
        """
        return self.data["name"]
    
    def get_nickname(self) -> str:
        """
        Get the nickname of this team.
        """
        return self.data["nickname"]

class Ryver:
    """
    A Ryver object containing login credentials and organization information.

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
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": "Basic " + b64encode((user + ":" + password).encode("ascii")).decode("ascii")
        }
        self.url_prefix = "https://" + org + ".ryver.com/api/1/odata.svc/"
    
    def get_object(self, obj_type: str, obj_id: int) -> Object:
        """
        Get an object from Ryver with a type and ID.

        Note that this method does send requests, so it may take some time.
        """
        url = self.url_prefix + f"{obj_type}({obj_id})"
        resp = requests.get(url, headers = self.headers)
        resp.raise_for_status()
        return TYPES_DICT[obj_type](self, obj_type, resp.json()["d"]["results"])

    def get_chats(self, obj_type: str, top: int = -1, skip: int = 0) -> typing.List[Chat]:
        """
        Get a list of chats (teams, forums, users, etc) from Ryver.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        Note that this method does send requests, so it may take some time.
        Consider using get_cached_chats() to cache the data in a JSON file.
        """
        url = self.url_prefix + obj_type
        chats = get_all(url, self.headers, top=top, skip=skip)
        return [TYPES_DICT[obj_type](self, obj_type, chat) for chat in chats]
    
    def get_cached_chats(self, obj_type: str, force_update: bool = False, name: str = None, top: int = -1, skip: int = 0) -> typing.List[Chat]:
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
            chats = self.get_chats(obj_type, top=top, skip=skip)
            with open(name, "w") as f:
                json.dump([chat.data for chat in chats], f)
            return chats

TYPE_USER = "users"
TYPE_FORUM = "forums"
TYPE_TEAM = "workrooms"

TYPE_TOPIC = "posts"
TYPE_TOPIC_REPLY = "postComments"

# Note: messages aren't really a "real" type in the Ryver API
# They're just here for the sake of completeness and to fit in with the rest of pyryver
TYPE_MESSAGE = "messages"

ENTITY_TYPES = {
    TYPE_USER: "Entity.User",
    TYPE_FORUM: "Entity.Forum",
    TYPE_TEAM: "Entity.Workroom",
    TYPE_TOPIC: "Entity.Post",
    TYPE_MESSAGE: None,
    TYPE_TOPIC_REPLY: "Entity.Post.Comment",
}

TYPES_DICT = {
    TYPE_USER: User,
    TYPE_FORUM: Forum,
    TYPE_TEAM: Team,
    TYPE_TOPIC: Topic,
    TYPE_MESSAGE: Message,
    TYPE_TOPIC_REPLY: TopicReply,
}

FIELD_USER_USERNAME = "username"
FIELD_USER_EMAIL_ADDR = "emailAddress"
FIELD_USER_DISPLAY_NAME = "displayName"

FIELD_NAME = "name"
FIELD_NICKNAME = "nickname"
FIELD_ID = "id"

def get_obj_by_field(objs: typing.List[Object], field: str, value: typing.Any) -> Object:
    """
    Gets an object from a list of objects by a field.

    For example, this function can find a chat with a specific nickname in a
    list of chats.
    """
    for obj in objs:
        if obj.data[field] == value:
            return obj
    return None

def get_all(url: str, headers: dict, top: int = -1, skip: int = 0, param: str = "?$skip"):
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

        resp = requests.get(url + f"{param}={skip}&$top={count}", headers=headers)
        resp.raise_for_status()
        page = resp.json()["d"]["results"]
        result.extend(page)
        if len(page) == 0 or top == 0:
            break
        skip += len(page)
    return result

def get_type_from_entity(entity_type: str) -> str:
    """
    Gets the object type from the entity type

    Note that it doesn't actually return a class, just the string
    """
    for t, e in ENTITY_TYPES.items():
        if e == entity_type:
            return t

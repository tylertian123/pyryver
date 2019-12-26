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

class Topic(Object):
    """
    A Ryver topic in a chat.
    """

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
    
    def get_author(self):
        """
        Get the author of this message, as a User object.

        Note that this method does send requests, so it may take some time.
        """
        return self.cred.get_object(TYPE_USER, self.data["from"]["id"])

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
    
    def get_topics(self, archived: bool = False) -> typing.List[Topic]:
        """
        Get all the topics in this chat.

        Note that this method does send requests, so it may take some time.
        """
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
        topics = get_all(url, self.cred.headers, "&$skip")
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

    def get_chats(self, obj_type: str) -> typing.List[Chat]:
        """
        Get a list of chats (teams, forums, users, etc) from Ryver.

        Note that this method does send requests, so it may take some time.
        Consider using get_cached_chats() to cache the data in a JSON file.
        """
        url = self.url_prefix + obj_type
        chats = get_all(url, self.headers)
        return [TYPES_DICT[obj_type](self, obj_type, chat) for chat in chats]
    
    def get_cached_chats(self, obj_type: str, force_update: bool = False, name: str = None) -> typing.List[Chat]:
        """
        Attempt to load a list of chats (teams, forums, users, etc) from JSON,
        and if not found, get them from Ryver.

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
            chats = self.get_chats(obj_type)
            with open(name, "w") as f:
                json.dump([chat.data for chat in chats], f)
            return chats

TYPE_USER = "users"
TYPE_FORUM = "forums"
TYPE_TEAM = "workrooms"

TYPE_TOPIC = "posts"

# Note: messages aren't really a "real" type in the Ryver API
# They're just here for the sake of completeness and to fit in with the rest of pyryver
TYPE_MESSAGE = "messages"

ENTITY_TYPES = {
    TYPE_USER: "Entity.User",
    TYPE_FORUM: "Entity.Forum",
    TYPE_TEAM: "Entity.Workroom",
    TYPE_TOPIC: "Entity.Post",
    TYPE_MESSAGE: None,
}

TYPES_DICT = {
    TYPE_USER: User,
    TYPE_FORUM: Forum,
    TYPE_TEAM: Team,
    TYPE_TOPIC: Topic,
    TYPE_MESSAGE: Message,
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

def get_all(url: str, headers: dict, param: str = "?$skip"):
    """
    Because the REST API only gives 50 results at a time, this function is used
    to retrieve all objects.

    Intended for internal use only.
    """
    result = []
    skip = 0
    while True:
        resp = requests.get(url + f"{param}={skip}", headers=headers)
        resp.raise_for_status()
        page = resp.json()["d"]["results"]
        if len(page) == 0:
            break
        result.extend(page)
        skip += len(page)
    return result

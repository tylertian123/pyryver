import requests
from base64 import b64encode
from getpass import getpass
import typing
import os
import json

class Creator:
    def __init__(self, name: str, avatar: str):
        self.name = name
        self.avatar = avatar
    
    def to_dict(self) -> dict:
        return {
            "displayName": self.name,
            "avatar": self.avatar
        }

class Object:
    def __init__(self, cred, obj_type: str, data: dict):
        self.cred = cred
        self.data = data
        self.obj_type = obj_type
        self.entity_type = ENTITY_TYPES[obj_type]
        self.id = data["id"]

class Topic(Object):
    pass

class Chat(Object):
    def send_message(self, message: str, creator: Creator = None) -> str:
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
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
        topics = get_all(url, self.cred.headers, "&$skip")
        return [Topic(self.cred, TYPE_TOPIC, data) for data in topics]

class User(Chat):
    def set_activated(self, activated: bool) -> None:
        url = self.cred.url_prefix + f"{self.obj_type}({self.id})/User.Active.Set(value='{'true' if activated else 'false'}')"
        resp = requests.post(url, headers=self.cred.headers)
        resp.raise_for_status()

class Forum(Chat):
    pass

class Team(Chat):
    pass

class Ryver:
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
    
    def get_chats(self, obj_type: str) -> typing.List[Chat]:
        url = self.url_prefix + obj_type
        chats = get_all(url, self.headers)
        return [TYPES_DICT[obj_type](self, obj_type, chat) for chat in chats]
    
    def get_cached_chats(self, obj_type: str, name: str = None) -> typing.List[Chat]:
        name = name or "pyryver." + obj_type + ".json"
        if os.path.exists(name):
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

ENTITY_TYPES = {
    TYPE_USER: "Entity.User",
    TYPE_FORUM: "Entity.Forum",
    TYPE_TEAM: "Entity.Workroom",
    TYPE_TOPIC: "Entity.Post",
}

TYPES_DICT = {
    TYPE_USER: User,
    TYPE_FORUM: Forum,
    TYPE_TEAM: Team,
    TYPE_TOPIC: Topic,
}

FIELD_USER_USERNAME = "username"
FIELD_USER_EMAIL_ADDR = "emailAddress"
FIELD_USER_DISPLAY_NAME = "displayName"

FIELD_NAME = "name"
FIELD_NICKNAME = "nickname"
FIELD_ID = "id"

def get_obj_by_field(objs: typing.List[Object], field: str, value: typing.Any) -> Object:
    for obj in objs:
        if obj.data[field] == value:
            return obj
    return None

def get_all(url: str, headers: dict, param: str = "?$skip"):
    """
    Because the REST API only gives 50 results at a time, this function is used
    to retrieve all objects.
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

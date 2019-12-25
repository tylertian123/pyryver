import requests
from base64 import b64encode
from getpass import getpass
import os
import json

class Credentials:
    def __init__(self, org=None, user=None, password=None):
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

TYPE_USERS = "users"
TYPE_FORUMS = "forums"
TYPE_TEAMS = "workrooms"

ENTITY_TYPES = {
    TYPE_USERS: "Entity.User",
    TYPE_FORUMS: "Entity.Forum",
    TYPE_TEAMS: "Entity.Workroom"
}

FIELD_USER_USERNAME = "username"
FIELD_USER_EMAIL_ADDR = "emailAddress"
FIELD_USER_DISPLAY_NAME = "displayName"

FIELD_NAME = "name"
FIELD_NICKNAME = "nickname"
FIELD_ID = "id"

def get_list(cred, objtype):
    url = cred.url_prefix + objtype
    resp = requests.get(url, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()["d"]["results"]

def get_cached_list(cred, objtype, name=None):
    name = name or "pyryver." + objtype + ".json"
    if os.path.exists(name):
        with open(name, "r") as f:
            return json.load(f)
    else:
        data = get_list(cred, objtype)
        with open(name, "w") as f:
            json.dump(data, f)
        return data

def get_obj_by_field(objs, field, value):
    for obj in objs:
        if obj[field] == value:
            return obj
    return None

def get_topics(cred, objtype, objid, archived=False):
    url = cred.url_prefix + f"{objtype}({objid})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
    resp = requests.get(url, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()["d"]["results"]

def creator(name, avatar):
    return {
        "displayName": name,
        "avatar": avatar
    }

def create_topic(cred, objtype, objid, subject, body, creator=None):
    url = cred.url_prefix + "posts"
    data = {
        "body": body,
        "subject": subject,
        "outAssociations": {
            "results": [
                {
                    "inSecured": True,
                    "inType": ENTITY_TYPES[objtype],
                    "inId": objid
                }
            ]
        },
        "recordType": "note"
    }
    if creator:
        data["createSource"] = creator
    resp = requests.post(url, json=data, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()["d"]["results"]

def send_message(cred, objtype, objid, message, creator=None):
    url = cred.url_prefix + f"{objtype}({objid})/Chat.PostMessage()"
    data = {
        "body": message
    }
    if creator:
        data["createSource"] = creator
    resp = requests.post(url, json=data, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()["d"]

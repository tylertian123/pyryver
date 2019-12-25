import requests
from base64 import b64encode
from getpass import getpass

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

def get_list(cred, objtype):
    url = cred.url_prefix + objtype
    resp = requests.get(url, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()["d"]["results"]

def get_topics(cred, objtype, objid, archived=False):
    url = cred.url_prefix + f"{objtype}({objid})/Post.Stream(archived={'true' if archived else 'false'})?$format=json"
    resp = requests.get(url, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()["d"]["results"]

def send_message(cred, objtype, objid, message, displayName=None, avatarURL=None):
    url = cred.url_prefix + f"{objtype}({objid})/Chat.PostMessage()"
    data = {
        "body": message
    }
    if displayName or avatarURL:
        data["createSource"] = {}
        if displayName:
            data["createSource"]["displayName"] = displayName
        if avatarURL:
            data["createSource"]["avatar"] = avatarURL
    resp = requests.post(url, json=data, headers=cred.headers)
    resp.raise_for_status()
    return resp.json()

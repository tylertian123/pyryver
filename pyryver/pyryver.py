"""
A simple Python library for Ryver's REST APIs.
"""

import aiohttp
import asyncio
import typing
import os
import json
from getpass import getpass
from pyryver import ryver_ws
from pyryver.util import *
from pyryver.objects import *
from pyryver.cache_storage import *

class Ryver:
    """
    A Ryver session contains login credentials and organization information.

    This is the starting point for any application using pyryver.
    """

    def __init__(self, org: str = None, user: str = None, password: str = None, cache: typing.Type[AbstractCacheStorage] = None):
        """
        Create a new session. 

        If the organization or username is not provided, it will be prompted 
        using input(). If the password is not provided, it will be prompted 
        using getpass().

        The cache is used to load the chats data. If not provided, no caching
        will occur.

        If a valid cache is provided, the chats data will be loaded in the
        constructor. Otherwise, it must be loaded through load_forums(),
        load_teams() and load_users() or load_chats().
        """
        if not org:
            org = input("Organization: ")
        if not user:
            user = input("Username: ")
        if not password:
            password = getpass()

        self._url_prefix = "https://" + org + ".ryver.com/api/1/odata.svc/"
        self._session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(user, password), raise_for_status=True)

        self._cache = cache
        # Try to load from cache if it exists
        if cache:
            self.users = cache.load(self, TYPE_USER) or None
            self.forums = cache.load(self, TYPE_FORUM) or None
            self.teams = cache.load(self, TYPE_TEAM) or None
        else:
            self.users = None
            self.forums = None
            self.teams = None

    async def __aenter__(self):
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc, *exc_info):
        return await self._session.__aexit__(exc, *exc_info)
    
    async def _get_chats(self, obj_type: str, top: int = -1, skip: int = 0) -> typing.List[Chat]:
        """
        Get a list of chats (teams, forums, users, etc) from Ryver.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        This method sends requests.
        Consider using get_cached_chats() to cache the data in a JSON file.
        """
        url = self._url_prefix + obj_type
        chats = await get_all(session=self._session, url=url, top=top, skip=skip)
        return [TYPES_DICT[obj_type](self, obj_type, chat) for chat in chats]

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
    
    async def load_users(self) -> None:
        """
        Load the data of all users.

        This refreshes the cached data if a cache is supplied.
        """
        self.users = await self._get_chats(TYPE_USER)
        if self._cache:
            self._cache.save(TYPE_USER, self.users)
    
    async def load_forums(self) -> None:
        """
        Load the data of all forums.

        This refreshes the cached data if a cache is supplied.
        """
        self.forums = await self._get_chats(TYPE_FORUM)
        if self._cache:
            self._cache.save(TYPE_FORUM, self.forums)
    
    async def load_teams(self) -> None:
        """
        Load the data of all teams.

        This refreshes the cached data if a cache is supplied.
        """
        self.teams = await self._get_chats(TYPE_TEAM)
        if self._cache:
            self._cache.save(TYPE_TEAM, self.teams)
    
    async def load_chats(self) -> None:
        """
        Load the data of all users/teams/forums. 

        This refreshes the cached data if a cache is supplied.
        """
        self.users = await self._get_chats(TYPE_USER)
        self.forums = await self._get_chats(TYPE_FORUM)
        self.teams = await self._get_chats(TYPE_TEAM)
        if self._cache:
            self._cache.save(TYPE_USER, self.users)
            self._cache.save(TYPE_FORUM, self.forums)
            self._cache.save(TYPE_TEAM, self.teams)

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
        notifs = await get_all(session=self._session, url=url, top=top, skip=skip, param_sep="&")
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
    
    async def get_info(self) -> typing.Dict[str, typing.Any]:
        """
        Get organization and user info.

        This method returns an assortment of info. It is currently the only way
        to get avatar URLs for users/teams/forums etc.
        The results include:
         - Basic user info - contains avatar URLs ("me")
         - User UI preferences ("prefs")
         - Ryver app info ("app")
         - Basic info about all users - contains avatar URLs ("users")
         - Basic info about all teams - contains avatar URLs ("teams")
         - Basic info about all forums - contains avatar URLs ("forums")
         - All available commands ("commands")
         - "messages" and "prefixes", the purpose of which are currently unknown.

        This method sends requests.
        """
        url = self._url_prefix + f"Ryver.Info()?$format=json"
        async with self._session.get(url) as resp:
            return (await resp.json())["d"]
    
    def get_live_session(self) -> ryver_ws.RyverWS:
        """
        Get a live session.
        
        The session is not started unless start() is called or if it is used as
        a context manager.
        """
        return ryver_ws.RyverWS(self)

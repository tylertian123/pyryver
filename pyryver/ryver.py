"""
This module contains the :py:class:`Ryver` class, which is the starting point for any
application using pyryver.
"""

import aiohttp
import typing
from . import doc
from getpass import getpass
from pyryver import ryver_ws
from .util import *
from .objects import *
from .cache_storage import *


class Ryver:
    """
    A Ryver session contains login credentials and organization information.

    This is the starting point for any application using pyryver.

    If the organization, it will be prompted using input(). 
    If the username or password are not provided, and the token is not provided,
    the username and password will be prompted.

    If a token is specified, the username and password will be ignored.

    The cache is used to load the chats data. If not provided, no caching
    will occur.

    If a valid cache is provided, the chats data will be loaded in the
    constructor. Otherwise, it must be loaded through load_forums(),
    load_teams() and load_users() or load_chats().

    :param org: Your organization's name (optional). (as seen in the URL)
    :param user: The username to authenticate with (optional).
    :param password: The password to authenticate with (optional).
    :param token: The custom integration token to authenticate with (optional).
    :param cache: The aforementioned cache (optional).
    """

    def __init__(self, org: str = None, user: str = None, password: str = None, token: str = None,
                 cache: typing.Type[AbstractCacheStorage] = None):
        if org is None:
            org = input("Organization: ")
        if user is None and token is None:
            user = input("Username: ")
        if password is None and token is None:
            password = getpass()

        self.org = org
        
        self._url_prefix = "https://" + org + ".ryver.com/api/1/odata.svc/"
        if token is None:
            self._session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(user, password), raise_for_status=True)
        else:
            headers = {
                "Authorization": f"Bearer {token}"
            }
            self._session = aiohttp.ClientSession(
                headers=headers, raise_for_status=True)

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

    async def __aenter__(self) -> "Ryver":
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc, *exc_info):
        return await self._session.__aexit__(exc, *exc_info)

    async def _get_chats(self, obj_type: str, top: int = -1, skip: int = 0) -> typing.List[Chat]:
        """
        Get a list of chats (teams, forums, users, etc) from Ryver.

        top is the maximum number of results (-1 for unlimited), skip is how
        many results to skip.

        .. warning::
           This method is intended for internal use only.

        :param obj_type: The type of the chats.
        :param top: The max number of results (optional).
        :param skip: The number of results to skip (optional).
        :return: The chats.
        """
        url = self.get_api_url(obj_type)
        return [TYPES_DICT[obj_type](self, chat) async for chat in self.get_all(url=url, top=top, skip=skip)]

    async def close(self):
        """
        Close this session.
        """
        await self._session.close()

    def get_api_url(self, obj_type: str = None, obj_id: int = None, action: str = None, **kwargs) -> str:
        """
        Get the URL for making an API request.

        .. warning::
           This method is intended for internal use only.

        The formatted url will have the form ``"{prefix}/{type}({id})/{action}?{additional_params}"``.
        If any parameter is unspecified, they will be omitted.

        If extra keyword arguments are supplied, they are appended to the request
        as additional query parameters. Possible values include ``top``, ``skip``, 
        ``select``, ``expand`` and more. 
        The `Ryver Developer Docs <https://api.ryver.com/ryvrest_api_examples.html>`_
        contains documentation for some of these parameters.

        :param obj_type: The type of the object to work with for this API request, a constant beginning with ``TYPE_`` in :ref:`pyryver.util <util-data-constants>` (optional).
        :param obj_id: The object's ID (optional).
        :param action: The action to take on the object (optional).
        :return: The formatted API url.
        """
        url = self._url_prefix
        if obj_type is not None:
            url += str(obj_type)
        if obj_id is not None:
            url += f"({obj_id})"
        if action is not None:
            if not url.endswith("/"):
                url += "/"
            url += str(action)
        if kwargs:
            url += "?" + "&".join(f"${k}={v}" for k, v in kwargs.items())
        return url

    async def get_all(self, url: str, top: int = -1, skip: int = 0) -> typing.AsyncIterator[dict]:
        """
        Get all objects from an URL, without the typical 50 result limit.

        .. warning::
           This function is intended for internal use only.

        :param url: The url to request from.
        :param top: The max number of results, or -1 for unlimited (optional).
        :param skip: The number of results to skip (optional).
        :return: An async iterator for the results (raw data).
        """
        param_sep = "&" if "?" in url else "?"
        # -1 means everything
        if top == -1:
            top = float("inf")
        while True:
            # Respect the max specified
            count = min(top, 50)
            top -= count

            request_url = url + f"{param_sep}$skip={skip}&$top={count}"
            async with self._session.get(request_url) as resp:
                page = (await resp.json())["d"]["results"]

            for i in page:
                yield i
            if not page or top == 0:
                break
            skip += len(page)

    async def get_object(self, obj_type: typing.Union[str, type], obj_id: int, **kwargs) -> typing.Type[Object]:
        """
        Get an object from Ryver with a type and ID.

        If extra keyword arguments are supplied, they are appended to the request
        as additional query parameters. Possible values include ``top``, ``skip``, 
        ``select``, ``expand`` and more. 
        The `Ryver Developer Docs <https://api.ryver.com/ryvrest_api_examples.html>`_
        contains documentation for some of these parameters.

        :param obj_type: The type of the object to retrieve, either a string type or the actual object type.
        :param obj_id: The object's ID.
        :raises TypeError: If the object is not instantiable.
        :return: The object requested.
        """
        if not isinstance(obj_type, str):
            if not obj_type.is_instantiable():
                raise TypeError(f"The type {obj_type.__name__} is not instantiable!")
            obj_type = obj_type.get_type()
        async with self._session.get(self.get_api_url(obj_type, obj_id, action=None, **kwargs)) as resp:
            return TYPES_DICT[obj_type](self, (await resp.json())["d"]["results"])

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

    async def load_missing_chats(self) -> None:
        """
        Load the data of all users/teams/forums if it does not exist.

        Unlike load_chats(), this does not update the cache.

        This method could send requests.
        """
        if self.users is None:
            await self.load_users()
        if self.forums is None:
            await self.load_forums()
        if self.teams is None:
            await self.load_teams()

    def get_user(self, **kwargs) -> User:
        """
        Get a specific user.

        If no query parameters are supplied, more than one query parameters are
        supplied or users are not loaded, raises :py:class:`ValueError`.

        Allowed query parameters are:

        - id
        - jid
        - username
        - name/display_name
        - email

        If using username or email to find the user, the search will be case-insensitive.

        Returns None if not found.

        :return: The user, or None of not found.
        """
        if self.users is None:
            raise ValueError("Users not loaded")
        if len(kwargs.items()) != 1:
            raise ValueError("Only 1 query parameter can be specified!")
        field, value = list(kwargs.items())[0]
        if field == "name":
            field = "display_name"
        # Do a case insensitive search for usernames and emails
        case_sensitive = True
        if field == "username" or field == "email":
            case_sensitive = False
        try:
            return get_obj_by_field(self.users, FIELD_NAMES[field], value, case_sensitive)
        except KeyError:
            raise ValueError("Invalid query parameter!")

    def get_groupchat(self, **kwargs) -> GroupChat:
        """
        Get a specific forum/team.

        If no query parameters are supplied, more than one query parameters are
        supplied or forums/teams are not loaded, raises :py:class:`ValueError`.

        Allowed query parameters are:

        - id
        - jid
        - name
        - nickname

        If using nickname to find the chat, the search will be case-insensitive.

        Returns None if not found.

        :return: The chat, or None if not found.
        """
        if self.forums is None or self.teams is None:
            raise ValueError("Forums/teams not loaded")
        if len(kwargs.items()) != 1:
            raise ValueError("Only 1 query parameter can be specified!")
        field, value = list(kwargs.items())[0]
        # Case-insensitive search for nicknames
        case_sensitive = True
        if field == "nickname":
            case_sensitive = False
        try:
            return get_obj_by_field(self.forums + self.teams, FIELD_NAMES[field], value, case_sensitive)
        except KeyError:
            raise ValueError("Invalid query parameter!")

    def get_chat(self, **kwargs) -> Chat:
        """
        Get a specific forum/team/user.

        If no query parameters are supplied, more than one query parameters are
        supplied or forums/teams/users are not loaded, raises :py:class:`ValueError`.

        Allowed query parameters are:

        - id
        - jid

        Returns None if not found.

        :return: The chat, or None if not found.
        """
        if self.forums is None or self.teams is None or self.users is None:
            raise ValueError("Forums/teams/users not loaded")
        if len(kwargs.items()) != 1:
            raise ValueError("Only 1 query parameter can be specified!")
        field, value = list(kwargs.items())[0]
        # Case-insensitive search for usernames, emails and nicknames
        # If this function is used as intended as stated in the docs, these fields should never be used
        # however they still function correctly, so for consistency they're still implemented
        case_sensitive = True
        if field == "username" or field == "email" or field == "nickname":
            case_sensitive = False
        try:
            return get_obj_by_field(self.forums + self.teams + self.users, FIELD_NAMES[field], value, case_sensitive)
        except KeyError:
            raise ValueError("Invalid query parameter!")

    async def get_notifs(self, unread: bool = False, top: int = -1, skip: int = 0) -> typing.AsyncIterator[Notification]:
        """
        Get the notifications for the logged in user.

        :param unread: If True, only return unread notifications.
        :param top: Maximum number of results.
        :param skip: Skip this many results.
        :return: An async iterator for the user's notifications.
        """
        if unread:
            url = self.get_api_url(TYPE_NOTIFICATION, format="json",
                                   orderby="modifyDate desc", filter="((unread eq true))")
        else:
            url = self.get_api_url(
                TYPE_NOTIFICATION, format="json", orderby="modifyDate desc")

        async for notif in self.get_all(url=url, top=top, skip=skip):
            yield Notification(self, notif)

    async def mark_all_notifs_read(self) -> int:
        """
        Marks all the user's notifications as read.

        :return: How many notifications were marked as read.
        """
        url = self.get_api_url(
            TYPE_NOTIFICATION, action="UserNotification.MarkAllRead()", format="json")
        async with self._session.post(url) as resp:
            return (await resp.json())["d"]["count"]

    async def mark_all_notifs_seen(self) -> int:
        """
        Marks all the user's notifications as seen.

        :return: How many notifications were marked as seen.
        """
        url = self.get_api_url(
            TYPE_NOTIFICATION, action="UserNotification.MarkAllSeen()", format="json")
        async with self._session.post(url) as resp:
            return (await resp.json())["d"]["count"]

    async def upload_file(self, filename: str, filedata: typing.Any, filetype: str = None) -> Storage:
        """
        Upload a file to Ryver (for attaching to messages).

        .. note::
           Although this method uploads a file, the returned object is an instance of :py:class:`Storage`,
           with type :py:attr:`Storage.TYPE_FILE`.
           Use :py:meth:`Storage.get_file()` to obtain the actual ``File`` object.

        :param filename: The filename to send to Ryver. (this will show up in the UI if attached as an embed, for example)
        :param filedata: The file's raw data, sent directly to :py:meth:`aiohttp.FormData.add_field`.
        :param filetype: The MIME type of the file.
        :return: The uploaded file, as a :py:class:`Storage` object.
        """
        url = self.get_api_url(
            TYPE_STORAGE, action="Storage.File.Create(createFile=true)", expand="file", format="json")
        data = aiohttp.FormData(quote_fields=False)
        data.add_field("file", filedata, filename=filename,
                       content_type=filetype)
        async with self._session.post(url, data=data) as resp:
            return Storage(self, await resp.json())

    async def create_link(self, name: str, link_url: str) -> Storage:
        """
        Create a link on Ryver (for attaching to messages).

        .. note::
           The returned object is an instance of :py:class:`Storage` with type :py:attr:`Storage.TYPE_LINK`.

        :param name: The name of this link (its title).
        :param url: The URL of this link.
        :return: The created link, as a :py:class:`Storage` object.
        """
        url = self.get_api_url(
            TYPE_STORAGE, action="Storage.Link.Create()", format="json")
        data = {
            "description": False,
            "fileName": name,
            "showPreview": True,
            "url": link_url,
        }
        async with self._session.post(url, json=data) as resp:
            return Storage(self, await resp.json())

    async def get_info(self) -> typing.Dict[str, typing.Any]:
        """
        Get organization and user info.

        This method returns an assortment of info. It is currently the only way
        to get avatar URLs for users/teams/forums etc.
        The results (returned mostly verbatim from the Ryver API) include:

         - Basic user info - contains avatar URLs ("me")
         - User UI preferences ("prefs")
         - Ryver app info ("app")
         - Basic info about all users - contains avatar URLs ("users")
         - Basic info about all teams - contains avatar URLs ("teams")
         - Basic info about all forums - contains avatar URLs ("forums")
         - All available commands ("commands")
         - "messages" and "prefixes", the purpose of which are currently unknown.

        :return: The raw org and user info data.
        """
        url = self.get_api_url(action="Ryver.Info()", format="json")
        async with self._session.get(url) as resp:
            return (await resp.json())["d"]
    
    async def invite_user(self, email: str, role: str = User.USER_TYPE_MEMBER, username: str = None, 
                          display_name: str = None) -> User:
        """
        Invite a new user to the organization.

        An optional username and display name can be specified to pre-populate those
        values in the User Profile page that the person is asked to fill out when
        they accept their invite.

        :param email: The email of the user.
        :param role: The role of the user (member or guest), one of the ``User.USER_TYPE_`` constants (optional).
        :param username: The pre-populated username of this user (optional).
        :param display_name: The pre-populated display name of this user (optional).
        :return: The invited user object.
        """
        url = self.get_api_url(action="User.Invite()")
        data = {
            "email": email,
            "type": role,
        }
        if username is not None:
            data["username"] = username
        if display_name is not None:
            data["displayName"] = display_name
        async with self._session.post(url, json=data) as resp:
            return User(self, (await resp.json())["d"]["results"])

    async def _create_groupchat(self, chat_type: str, name: str, nickname: str, about: str, description: str) -> GroupChat:
        """
        Create a forum or team.

        .. warning::
           This method is intended for internal use only.
        
        :param chat_type: The type (forum or team).
        :param name: The name.
        :param nickname: The nickname.
        :param about: The "about" (or "purpose" in the UI).
        :param description: The description.
        :return: The created groupchat object.
        """
        url = self.get_api_url(action=chat_type)
        data = {
            "name": name
        }
        if nickname is not None:
            data["nickname"] = nickname
        if about is not None:
            data["about"] = about
        if description is not None:
            data["description"] = description
        async with self._session.post(url, json=data) as resp:
            return TYPES_DICT[chat_type](self, (await resp.json())["d"]["results"])
    
    async def create_team(self, name: str, nickname: str = None, about: str = None, description: str = None) -> Team:
        """
        Create a new private team.

        :param name: The name of this team.
        :param nickname: The nickname of this team (optional).
        :param about: The "about" (or "purpose" in the UI) of this team (optional).
        :param description: The description of this team (optional).
        :return: The created team object.
        """
        return await self._create_groupchat(TYPE_TEAM, name, nickname, about, description)
    
    async def create_forum(self, name: str, nickname: str = None, about: str = None, description: str = None) -> Forum:
        """
        Create a new open forum.

        :param name: The name of this forum.
        :param nickname: The nickname of this forum (optional).
        :param about: The "about" (or "purpose" in the UI) of this forum (optional).
        :param description: The description of this forum (optional).
        :return: The created forum object.
        """
        return await self._create_groupchat(TYPE_FORUM, name, nickname, about, description)

    @doc.acontexmanager
    def get_live_session(self) -> ryver_ws.RyverWS:
        """
        Get a live session.

        The session is not started unless start() is called or if it is used as
        a context manager.

        .. warning::
           Live sessions **do not work** when using a custom integration token.

        :return: The live websockets session.
        """
        return ryver_ws.RyverWS(self)

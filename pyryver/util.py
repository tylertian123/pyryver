import aiohttp
import asyncio
import typing

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

# Field names for get_obj_by_field
FIELD_USERNAME = "username"
FIELD_EMAIL_ADDR = "emailAddress"
FIELD_DISPLAY_NAME = "displayName"
FIELD_NAME = "name"
FIELD_NICKNAME = "nickname"
FIELD_ID = "id"
FIELD_JID = "jid"

FIELD_NAMES = {
    "id": FIELD_ID,
    "email": FIELD_EMAIL_ADDR,
    "username": FIELD_USERNAME,
    "display_name": FIELD_DISPLAY_NAME, 
    "jid": FIELD_JID,
    "nickname": FIELD_NICKNAME,
    "name": FIELD_NAME,
}

# Notification predicates
# Here only for backwards compatibility, use the ones in the notification class
NOTIF_PREDICATE_MENTION = "chat_mention"
NOTIF_PREDICATE_GROUP_MENTION = "group_mention"
NOTIF_PREDICATE_COMMENT = "commented_on"
NOTIF_PREDICATE_TASK_COMPLETED = "completed"


def get_type_from_entity(entity_type: str) -> str:
    """
    Gets the object type from the entity type.

    Note that it doesn't actually return a class, just the string.

    Intended for internal use only.
    """
    for t, e in ENTITY_TYPES.items():
        if e == entity_type:
            return t


async def get_all(session: aiohttp.ClientSession, url: str, top: int = -1, skip: int = 0, param_sep: str = "?") -> typing.List[dict]:
    """
    Because the REST API only gives 50 results at a time, this function is used
    to retrieve all objects.

    Intended for internal use only.
    """
    # -1 means everything
    if top == -1:
        top = float("inf")
    while True:
        # Respect the max specified
        count = min(top, 50)
        top -= count

        request_url = url + f"{param_sep}$skip={skip}&$top={count}"
        async with session.get(request_url) as resp:
            page = (await resp.json())["d"]["results"]

        for i in page:
            yield i
        if len(page) == 0 or top == 0:
            break
        skip += len(page)

_T = typing.TypeVar("T")

async def retry_until_available(coro: typing.Awaitable[_T], *args, timeout: float = None, **kwargs) -> _T:
    """
    Repeatedly tries to do some action (usually getting a resource) until the
    resource becomes available or a timeout elapses.

    This function will try to run the given coroutine once every 0.5 seconds. If
    it results in a 404, the function tries again. Otherwise, the exception is
    raised.

    If it times out, an :py:exc:`asyncio.TimeoutError` will be raised.

    args and kwargs are passed to the coroutine.

    :param coro: The coroutine to run
    :param timeout: The timeout in seconds, or None for no timeout
    """
    async def _retry_inner():
        try:
            while True:
                try:
                    return await coro(*args, **kwargs)
                except aiohttp.ClientResponseError as e:
                    if e.status == 404:
                        await asyncio.sleep(0.5)
                    else:
                        raise e
        except asyncio.CancelledError:
            pass
    
    return await asyncio.wait_for(_retry_inner(), timeout)

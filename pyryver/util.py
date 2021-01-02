"""
This module contains various contants and utilities for both internal and external use.
"""

import aiohttp
import asyncio
import datetime
import typing

from . import objects


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


def get_obj_by_field(objs: typing.Union[typing.List["objects.Object"], typing.Iterable["objects.Object"]],
                     field: str, value: typing.Any, case_sensitive: str = True, binsearch: bool = False) -> typing.Optional["objects.Object"]:
    """
    Gets an object from a list of objects by a field.

    For example, this function can find a chat with a specific nickname in a
    list of chats.

    :param objs: List of objects to search in.
    :param field: The field's name (usually a constant beginning with ``FIELD_`` in
                  :ref:`pyryver.util <util-data-constants>`) within the object's
                  JSON data.
    :param value: The value to look for.
    :param case_sensitive: Whether the search should be case-sensitive. Can be useful
                           for fields such as username or nickname, which are
                           case-insensitive. If the field value is not a string, it will
                           be ignored. (Optional, default False).
    :param binsearch: Whether to use a binary search. If the input is not a list, this
                      argument will be ignored. (Optional, default False).
    :return: The object with the matching field, or None if not found.
    """
    if not case_sensitive and isinstance(value, str):
        value = value.casefold()
    if binsearch and isinstance(objs, list):
        # The bisect module does not support keys, so we can't use it
        lo = 0
        hi = len(objs)
        while lo < hi:
            i = (lo + hi) // 2
            data = objs[i]._data[field]
            if not case_sensitive and isinstance(data, str):
                data = data.casefold()
            if value == data:
                return objs[i]
            if value < data:
                hi = i
            else:
                lo = i + 1
    else:
        for obj in objs:
            data = obj._data[field]
            if not case_sensitive and isinstance(data, str):
                if data.casefold() == value:
                    return obj
            else:
                if obj._data[field] == value:
                    return obj
    return None


def get_type_from_entity(entity_type: str) -> typing.Optional[str]:
    """
    Gets the object type from the entity type.

    Note that it doesn't actually return a class, just the string.

    .. warning::
       This function is intended for internal use only.

    :param entity_type: The entity type of the object.
    :return: The regular type of the object, or None if an invalid type.
    """
    for t, e in objects.ENTITY_TYPES.items():
        if e == entity_type:
            return t
    return None


_T = typing.TypeVar("_T")


async def retry_until_available(action: typing.Callable[..., typing.Awaitable[_T]], *args,
                                timeout: typing.Optional[float] = None, retry_delay: float = 0.5, **kwargs) -> _T:
    """
    Repeatedly tries to do some action (usually getting a resource) until the
    resource becomes available or a timeout elapses.

    This function will try to run the given coroutine once every ``retry_delay`` seconds.
    If it results in a 404, the function tries again. Otherwise, the exception is
    raised.

    If it times out, an :py:exc:`asyncio.TimeoutError` will be raised.

    ``args`` and ``kwargs`` are passed to the coroutine.

    For example, this snippet will try to get a message from a chat by ID with a timeout
    of 5 seconds, retrying after 1 second if a 404 occurs:

    .. code-block:: python

       message = await pyryver.retry_until_available(chat.get_message, message_id, timeout=5.0, retry_delay=1.0)

    .. note::
       Do not "call" the coro first and pass a future to this function; instead, pass
       a reference to the coro directly, as seen in the example. This is done because
       a single future cannot be awaited multiple times, so a new one is created each
       time the function retries.

    :param action: The coroutine to run.
    :param timeout: The timeout in seconds, or None for no timeout (optional).
    :param retry_delay: The duration in seconds to wait before trying again (optional).
    :return: The return value of the coroutine.
    """
    async def _retry_inner():
        try:
            while True:
                try:
                    return await action(*args, **kwargs)
                except aiohttp.ClientResponseError as e:
                    if e.status == 404:
                        await asyncio.sleep(retry_delay)
                    else:
                        raise e
        except asyncio.CancelledError:
            pass

    return await asyncio.wait_for(_retry_inner(), timeout)


def iso8601_to_datetime(timestamp: str) -> datetime.datetime:
    """
    Convert an ISO 8601 timestamp as returned by the Ryver API into a datetime.

    .. warning::
       This function does not handle *all* valid ISO 8601 timestamps; it only tries to
       handle the ones returned by the Ryver API. It uses the simple format string
       ``"%Y-%m-%dT%H:%M:%S%z"`` to parse the timestamp.

       Therefore, this function should **not** be used for parsing any ISO timestamp;
       to do that, consider using ``dateutil.parser``, or some alternative method.

    :param timestamp: The ISO 8601 timestamp.
    """
    if timestamp.endswith("Z"):
        return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    return datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")


def datetime_to_iso8601(timestamp: datetime.datetime) -> str:
    """
    Convert a datetime into an ISO 8601 timestamp as used by the Ryver API.

    :param timestamp: The datetime to convert.
    """
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")

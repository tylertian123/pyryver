"""
Cache storages are used by :py:class:`Ryver` to cache organization data locally.

In large organizations with lots of data, caching can be used to make the program load
some organization data locally instead of fetching them from Ryver. This can
significantly improve program startup times.

Currently, the lists of all users, forums, and teams can be cached.

.. seealso::
   The :py:class:`Ryver` class
"""


import json
import os
import typing
from .objects import *
from abc import ABC, abstractmethod


class AbstractCacheStorage(ABC):
    """
    An abstract class defining the requirements for cache storages.

    A cache storage is used by the Ryver class to cache chats data to improve
    performance.
    """

    @abstractmethod
    def load(self, ryver: "Ryver", obj_type: str) -> typing.List[Object]:
        """
        Load all saved objects of a specific type.

        If no objects were saved, this method returns an empty list.

        :param ryver: The Ryver session to associate the objects with.
        :param obj_type: The type of the objects to load.
        :return: A list of saved objects of that type.
        """

    @abstractmethod
    def save(self, obj_type: str, data: typing.Iterable[Object]) -> None:
        """
        Save all objects of a specific type.

        :param obj_type: The type of the objects to save.
        :param data: The objects to save.
        """


class FileCacheStorage(AbstractCacheStorage):
    """
    A cache storage implementation using files.
    """

    def __init__(self, root_dir: str = ".", prefix: str = ""):
        """
        Create a file cache storage with an optional root directory and name prefix.

        :param root_dir: All cache files will be stored relative to this directory, which itself is relative to the current directory.
        :param prefix: All cache files will be prefixed with this string.
        """
        self._root_dir = root_dir
        self._prefix = prefix

    def load(self, ryver: "Ryver", obj_type: str) -> typing.List[Object]:
        """
        Load all saved objects of a specific type.

        If no objects were saved, this method returns an empty list.

        :param ryver: The Ryver session to associate the objects with.
        :param obj_type: The type of the objects to load.
        :return: A list of saved objects of that type.
        """
        name = os.path.join(self._root_dir, self._prefix + obj_type + ".json")
        if not os.path.exists(name):
            return []
        try:
            with open(name, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print("Warning: Invalid JSON in cache")
            return []
        return [TYPES_DICT[obj_type](ryver, obj_data) for obj_data in data]

    def save(self, obj_type: str, data: typing.Iterable[Object]) -> None:
        """
        Save all objects of a specific type.

        :param obj_type: The type of the objects to save.
        :param data: The objects to save.
        """
        name = os.path.join(self._root_dir, self._prefix + obj_type + ".json")
        obj_data = [obj.get_raw_data() for obj in data]
        with open(name, "w") as f:
            json.dump(obj_data, f)


from .ryver import *  # nopep8

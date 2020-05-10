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
        """
    
    @abstractmethod
    def save(self, obj_type: str, data: typing.List[Object]) -> None:
        """
        Save all objects of a specific type.
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
        return [TYPES_DICT[obj_type](ryver, obj_type, obj_data) for obj_data in data]
    
    def save(self, obj_type: str, data: typing.List[Object]) -> None:
        """
        Save all objects of a specific type.
        """
        name = os.path.join(self._root_dir, self._prefix + obj_type + ".json")
        obj_data = [obj.get_raw_data() for obj in data]
        with open(name, "w") as f:
            json.dump(obj_data, f)


from pyryver.ryver import *

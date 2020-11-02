"""
This module's sole purpose is to contain the version.

The version is in its separate module instead of being defined in __init__.py because
this way the version can be obtained without having to import everything else, which may
not be possible due to missing dependencies, thus breaking `setup.py install`.
"""
__version__ = "0.4.0a5"

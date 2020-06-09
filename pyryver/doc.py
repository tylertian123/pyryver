"""
This module contains utilities used to help with documentation generation.

It is not intended for public use.
"""


def contextmanager(func):
    """
    Sets ``__returns_contextmanager__`` of the function to true for sphinxcontrib-trio
    autodetection.
    """
    func.__returns_contextmanager__ = True
    return func

def acontexmanager(func):
    """
    Sets ``__returns_acontextmanager__`` of the function to true for sphinxcontrib-trio
    autodetection.
    """
    func.__returns_acontextmanager__ = True
    return func

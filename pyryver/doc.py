def sphinx_contextmanager(func):
    """
    Sets ``__returns_contextmanager__`` of the function to true for sphinxcontrib-trio
    autodetection.
    """
    func.__returns_contextmanager__ = True
    return func

def sphinx_acontexmanager(func):
    """
    Sets ``__returns_acontextmanager__`` of the function to true for sphinxcontrib-trio
    autodetection.
    """
    func.__returns_acontextmanager__ = True
    return func

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from tornado import ioloop
from tornado.concurrent import run_on_executor
from tornado import gen
from functools import wraps
import threading

executors = {
    'short': ThreadPoolExecutor(max_workers=8),  # For little things to avoid blocking the main thread
    'long': ThreadPoolExecutor(max_workers=4),  # For longer work, like file I/O
    'aurora': ThreadPoolExecutor(max_workers=4),  # Exclusively for communicating with Aurora
    'docker': ThreadPoolExecutor(max_workers=4)  # Exclusively for communicating with Docker
}


def usepool(executor):
    """
    Decorator that runs the decorated function asynchronously in the given executor pool whenever it's run.
    Anything calling a function decorated with this decorator must be a gen.coroutine.
    """
    def dec(func):
        @wraps(func)
        @gen.coroutine
        def inner(*args, **kwargs):
            t = Task(executor)
            ret = yield t.run(func, *args, **kwargs)
            raise gen.Return(ret)
        return inner
    return dec


class Task:
    """
    Class that turns any function into an asynchronous call.
    Usage: t = Task( 'executorname' )
    result = yield t.run( fn, *args, **kwargs )
    Caller must be a gen.coroutine.
    """

    def __init__(self, executor):
        self.executor = executors[executor]
        self.io_loop = ioloop.IOLoop.instance()

    @run_on_executor
    def run(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)


class ThreadedDict(object):
    """A dict of values keyed by thread id."""
    def __init__(self, ctor_func):
        self.ctor_func = ctor_func
        self._thrdict = dict()

    def get(self):
        """Get the ID of the current thread. If there exists a value in the dict for that thread, return it.
        Otherwise, construct one and return that."""
        thrid = threading.get_ident()
        try:
            return self._thrdict[thrid]
        except KeyError:
            #No value! Create it.
            self._thrdict[thrid] = self.ctor_func()

        return self._thrdict[thrid]

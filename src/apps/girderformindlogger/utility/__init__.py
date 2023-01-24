# -*- coding: utf-8 -*-
import datetime
import errno
import json
import os
import re
import string
import time

import cherrypy
import dateutil.parser
import json5
import pytz
import requests
import six
from redis.exceptions import ConnectionError

from apps import girderformindlogger

try:
    from random import SystemRandom

    random = SystemRandom()
    random.random()  # potentially raises NotImplementedError
except NotImplementedError:
    girderformindlogger.logprint.warning(
        "WARNING: using non-cryptographically secure PRNG."
    )
    import random


def reconnect(name="default"):
    def repeat(func):
        def wrapper(*args, **kwargs):
            while True:
                try:
                    func(*args, **kwargs)
                except ConnectionError as e:
                    print(f"{name} was disconnected. Try to reconnect...")
                    time.sleep(2)

        return wrapper

    return repeat


def clean_empty(d):
    """
    The {..} construct is a dictionary comprehension; it'll only include keys
    from the original dictionary if v is true, e.g. not empty. Similarly the
    [..] construct builds a list.

    The nested (.. for ..) constructs are generator expressions that allow the
    code to compactly filter empty objects after recursing.

    Note that any values set to numeric 0 (integer 0, float 0.0) will also be
    cleared. You can retain numeric 0 values with if v or v == 0.

    https://stackoverflow.com/a/27974027/7868821
    """
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v is not None]
    return {
        k: v
        for k, v in ((k, clean_empty(v)) for k, v in d.items())
        if v is not None
    }


def parseTimestamp(x, naive=True):
    """
    Parse a datetime string using the python-dateutil package.

    If no timezone information is included, assume UTC. If timezone information
    is included, convert to UTC.

    If naive is True (the default), drop the timezone information such that a
    naive datetime is returned.
    """
    dt = dateutil.parser.parse(x)
    if dt.tzinfo:
        dt = dt.astimezone(pytz.utc).replace(tzinfo=None)
    if naive:
        return dt
    else:
        return pytz.utc.localize(dt)


def genToken(length=64):
    """
    Use this utility function to generate a random string of a desired length.
    """
    return "".join(
        random.choice(string.ascii_letters + string.digits)
        for _ in range(length)
    )


def camelcase(value):
    """
    Convert a module name or string with underscores and periods to camel case.

    :param value: the string to convert
    :type value: str
    :returns: the value converted to camel case.
    """
    return "".join(
        x.capitalize() if x else "_" for x in re.split("[._]+", value)
    )


def firstLower(value):
    """
    Make the first letter of a string lowercase.

    :param value: the string to convert
    :type value: str
    :returns: the value with the first character lowercased
    """
    return "".join([value[0].lower(), value[1:]])


def loadJSON(url, urlType="protocol"):
    from apps.girderformindlogger.exceptions import ValidationException

    print("Loading {} from {}".format(urlType, url))
    try:
        r = requests.get(url)
        data = json5.loads(r.text)
    except:
        return {}
        raise ValidationException("Invalid " + urlType + " URL: " + url, "url")
    return data


def mkdir(path, mode=0o777, recurse=True, existOk=True):
    """
    Create a new directory or ensure a directory already exists.

    :param path: The directory to create.
    :type path: str
    :param mode: The mode (permission mask) prior to applying umask.
    :type mode: int
    :param recurse: Whether intermediate missing dirs should be created.
    :type recurse: bool
    :param existOk: Set to True to suppress the error if the dir exists.
    :type existOk: bool
    """
    method = os.makedirs if recurse else os.mkdir

    try:
        method(path, mode)
    except OSError as exc:
        if existOk and exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def toBool(val):
    """
    Coerce a string value to a bool. Meant to be used to parse HTTP
    parameters, which are always sent as strings. The following string
    values will be interpreted as True:

      - ``'true'``
      - ``'on'``
      - ``'1'``
      - ``'yes'``

    All other strings will be interpreted as False. If the given param
    is not passed at all, returns the value specified by the default arg.
    This function is case-insensitive.

    :param val: The value to coerce to a bool.
    :type val: str
    """
    if isinstance(val, bool):
        return val

    return val.lower().strip() in ("true", "on", "1", "yes")


class JsonEncoder(json.JSONEncoder):
    """
    This extends the standard json.JSONEncoder to allow for more types to be
    sensibly serialized. This is used in Girder's REST layer to serialize
    route return values when JSON is requested.
    """

    def default(self, obj):
        event = girderformindlogger.events.trigger("rest.json_encode", obj)
        if len(event.responses):
            return event.responses[-1]

        if isinstance(obj, set):
            return tuple(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.replace(tzinfo=pytz.UTC).isoformat()
        return str(obj)


class RequestBodyStream(object):
    """
    Wraps a cherrypy request body into a more abstract file-like object.
    """

    _ITER_CHUNK_LEN = 65536

    def __init__(self, stream, size=None):
        self.stream = stream
        self.size = size

    def read(self, *args, **kwargs):
        return self.stream.read(*args, **kwargs)

    def close(self, *args, **kwargs):
        pass

    def __iter__(self):
        return self

    def __len__(self):
        return self.getSize()

    def __next__(self):
        data = self.read(self._ITER_CHUNK_LEN)
        if not data:
            raise StopIteration
        return data

    def next(self):
        return self.__next__()

    def getSize(self):
        """
        Returns the size of the body data wrapped by this class. For
        multipart encoding, this is the size of the part. For sending
        as the body, this is the Content-Length header.
        """
        if self.size is not None:
            return self.size

        return int(cherrypy.request.headers["Content-Length"])


def optionalArgumentDecorator(baseDecorator):
    """
    This decorator can be applied to other decorators, allowing the target decorator to be used
    either with or without arguments.

    The target decorator is expected to take at least 1 argument: the function to be wrapped. If
    additional arguments are provided by the final implementer of the target decorator, they will
    be passed to the target decorator as additional arguments.

    For example, this may be used as:

    .. code-block:: python

        @optionalArgumentDecorator
        def myDec(fun, someArg=None):
            ...

        @myDec
        def a(...):
            ...

        @myDec()
        def a(...):
            ...

        @myDec(5)
        def a(...):
            ...

        @myDec(someArg=5)
        def a(...):
            ...

    :param baseDecorator: The target decorator.
    :type baseDecorator: callable
    """

    @six.wraps(baseDecorator)
    def normalizedArgumentDecorator(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):  # Applied as a raw decorator
            decoratedFunction = args[0]
            # baseDecorator must wrap and return decoratedFunction
            return baseDecorator(decoratedFunction)
        else:  # Applied as a argument-containing decorator
            # Decoration will occur in two passes:
            #   * Now, the decorator arguments are passed, and a new decorator should be returned
            #   * Afterwards, the new decorator will be called to decorate the decorated function
            decoratorArgs = args
            decoratorKwargs = kwargs

            def partiallyAppliedDecorator(decoratedFunction):
                return baseDecorator(
                    decoratedFunction, *decoratorArgs, **decoratorKwargs
                )

            return partiallyAppliedDecorator

    return normalizedArgumentDecorator

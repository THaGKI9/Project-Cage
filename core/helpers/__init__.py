from collections import OrderedDict
from functools import wraps
from time import mktime

from flask import abort, jsonify, request
from flask_login import current_user

from core import app_config

from .signals import event_emitted  # noqa
from .renderer import RendererCollection  # noqa


def permission_require(permission):
    """A decorator to set up the permission of an interface of a view."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kargs):
            if app_config['ENABLE_PERMISSION_CONTROL'] \
                    and not current_user.can(permission):
                if request.blueprint == 'api':
                    # return restful result: json
                    # function to be decorate should be decorated by
                    # :meth:`core.helpers.restful` first
                    return {'permission': '权限不足，无法进行操作！'}
                else:
                    abort(403)
            return func(*args, **kargs)
        return wrapper
    return decorator


def restful(func):
    """A RESTful interface decorator.
    The decorated function should return a two-element tuple,
    (errors, data) and the final response will be format into json

    .. code-block:: javascript

        {
            $errors:  string or object,
            // data
        }
    """
    @wraps(func)
    def wrapper(*args, **kargs):
        rv_dict = OrderedDict()
        result = func(*args, **kargs)
        if not isinstance(result, tuple):
            result = (result, )

        if len(result) > 0:
            rv_dict['$errors'] = result[0]

        if len(result) > 1:
            rv_dict.update(result[1])

        return jsonify(rv_dict)
    return wrapper


def datetime_to_timestamp(dt):
    """Convert :class:`datetime.DateTime` object to timestamp in unit `ms`"""
    return int(mktime(dt.timetuple()) * 1000)


def make_raw_request_line():
    """Extract request information from :class:`flask.Request.environ` and
    format it into a standard request line."""
    request_line = ('%(REQUEST_METHOD)s %(PATH_INFO)s %(SERVER_PROTOCOL)s\r\n'
                    % request.environ)
    headers = '\r\n'.join(['%s: %s' % pair
                           for pair in request.headers.items()])
    return request_line + headers

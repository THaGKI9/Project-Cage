# flake8: noqa
from flask import Blueprint

# blueprint's ``url_prefix`` is set up when the app initializes.
bp = Blueprint('api', __name__)

from . import user

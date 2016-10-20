from sys import stderr
from traceback import format_exc

from flask import Flask, abort, current_app
from flask_babel import Babel
from flask_login import LoginManager
from playhouse.flask_utils import FlaskDB
from werkzeug.local import LocalProxy

db = FlaskDB()
login_manager = LoginManager()
babel = Babel()
app_config = LocalProxy(lambda: current_app.config)


def create_app(config):
    # Initialize Application
    app = Flask(__name__)
    app.config.from_object(config)
    config.init_app(app)

    # Configure Extensions
    from .models import AnonymousUser
    db.init_app(app)
    db.connect_db()
    babel.init_app(app)
    login_manager.init_app(app)
    login_manager.user_loader(user_loader)
    login_manager.anonymous_user = AnonymousUser

    # Configure Register
    from . import api, views
    app.register_blueprint(api.bp, url_prefix=app.config['API_URL_BASE'])
    app.register_blueprint(views.bp)

    # Configure Exception Handler
    from .helpers.signals import event_emitted
    event_emitted.connect(event_recorder, app)
    app.errorhandler(Exception)(exception_handler)

    return app


def user_loader(id):
    from .models import User
    try:
        return User.get(User.id == id)
    except User.DoesNotExist:
        return None


def event_recorder(sender, type, description, **kawargs):
    from sys import stderr
    from .models import Event
    try:
        Event.create(type=type, description=description)
    except Exception as ex:
        print('An exception occurs while recording an event.\r\n'
              '  Exception: ' + repr(ex),
              file=stderr)


def exception_handler(ex):
    from .helpers.signals import event_emitted
    event_emitted.send(
        current_app._get_current_object(),
        type='Exception',
        description=format_exc()
    )
    raise

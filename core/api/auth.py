from time import time

from flask import current_app, redirect, request
from flask_login import current_user, login_user, logout_user

from core import app_config
from core.helpers import restful, signals
from core.models import User

from . import bp


@bp.route('/login/')
@restful
def login():
    """``GET`` |API_URL_BASE|/login/

    Login, parameters are passed through query string.

    :param id: **Query**
    :param password: **Query**
    :param timestamp: **Query** client's timestamp(ms)
    :param remember: **Query** optional, boolean value

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            user: {
                id: string,
                name: string,
                role: {id: integer, name: string},
                expired: boolean,
                last_login: integer
            }
        }

        // failed
        {
            errors: {
                id: 'this user id does not exist.',
                password: 'user id can not match this password.',
                timestamp: 'login session is invalid any more. please refresh.'
            }
        }
    """
    id = request.args.get('id', '')
    password = request.args.get('password', '')
    client_timestamp = request.args.get('timestamp', 0, type=int)
    remember = request.args.get('remember', 'false') == 'true'

    try:
        user = User.get(User.id == id)
    except User.DoesNotExist:
        return {'id': '用户ID不存在'}

    if not user.check_password(password, client_timestamp):
        signals.event_emitted.send(
            current_app._get_current_object(),
            type='Auth: Login',
            description='user(%s) attempts to log in using wrong password.' %
                        user.id
        )
        return {'password': '用户ID与密码不匹配'}

    server_time = int(time() * 1000)
    time_pass = server_time - client_timestamp
    if abs(time_pass) > app_config['USER_LOGIN_TIMEOUT']:
        signals.event_emitted.send(
            current_app._get_current_object(),
            type='Auth: Login',
            description='user(%s) attempts to log in using expired timestamp.'
                        % user.id
        )
        return {'timestamp': '登陆会话超时，请刷新重试'}

    login_user(user, remember=remember)

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='Auth: Login',
        description='user(%s) login.' % user.id
    )

    return None, {'user': user.to_dict()}


@bp.route('/logout/')
def logout():
    """Logout and redirect to referrer page.

    Although this method is not a restful interface, to put it
    here seems comfortable. ^_^
    """
    if current_user.is_authenticated:
        signals.event_emitted.send(
            current_app._get_current_object(),
            type='Auth: Logout',
            description='user(%s) logout.' % current_user.get_id()
        )

        logout_user()

    return redirect(request.referrer)

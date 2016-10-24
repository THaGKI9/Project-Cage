from re import match as re_match

from flask import current_app, request
from flask_login import current_user

from core import app_config
from core.helpers import permission_require, restful, signals
from core.models import Permission, User

from . import bp


@bp.route('/users/')
@restful
@permission_require(Permission.READ_USER)
def get_users():
    """``GET`` |API_URL_BASE|/users/

    Get information of all users.

    :param limit: **Query** limit amount of user per page,
        default: |USER_LIST_DEFAULT_LIMIT|
    :param page: **Query**  page control, start from zero, default: 1

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            users: [
                {
                    id: string,
                    name: string,
                    role: {id: integer, name: string},
                    expired: boolean,
                    last_login: integer
                }
            ]
        }

    Permission required: ``READ_USER``
    """
    default_limit = app_config['USER_LIST_DEFAULT_LIMIT']
    limit = request.args.get('limit', default_limit, type=int)
    page = request.args.get('page', 1, type=int)

    limit = default_limit if limit <= 0 else limit
    page = 0 if page <= 0 else page

    users = User.select().order_by(User.create_time).paginate(page, limit)

    return None, {'users': [user.to_dict() for user in users]}


@bp.route('/user/<id>')
@restful
@permission_require(Permission.READ_USER)
def get_user(id):
    """``GET`` |API_URL_BASE|/user/:user_id

    Get information of a user.

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            users: {
                id: string,
                name: string,
                role: {id: integer, name: string},
                expired: boolean,
                last_login: integer
            ]
        }

        // failed
        {$errors: {id: 'this user does not exist.'}}

    Permission required: ``READ_USER``
    """
    try:
        user = User.get(User.id == id)
    except User.DoesNotExist as ex:
        return {'id': '该用户不存在！'}

    return None, {'user': user.to_dict()}


@bp.route('/user/', methods=['POST'])
@restful
@permission_require(Permission.CREATE_USER)
def add_user():
    """``POST`` |API_URL_BASE|/user/

    Add a new user.

    :param id: **JSON Param** user id
    :param name: **JSON Param** user name
    :param array permission: **JSON Param**
    :param password: **JSON Param** plain password, without encoding
    :param expired: **JSON Param** true or false, default: false

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            user: {
                id: string,
                name: string,
                expired: boolean,
                last_login: integer
            }
        }

        // failed
        {
            $errors: {
                id: 'this id is invalid'.
                name: 'this name is invalid.',
                password: 'this password is invalid',
                permission 'this permission identity is not defined.',
                id: 'this id is duplicated.',
                name: 'this name is duplicated.'
            }
        }

    Permission require: ``CREATE_USER``
    """
    config = app_config
    json = request.get_json()

    user_id = json.get('id', '').strip()
    if not re_match(config['USER_USERID_PATTERN'], user_id):
        return {'id': config['USER_USERID_DESCRIPTION']}

    name = json.get('name', '').strip()
    if not re_match(config['USER_NAME_PATTERN'], name):
        return {'name': config['USER_NAME_DESCRIPTION']}

    permission_list = json.get('permission', [])
    permission_value = Permission.parse_permission(permission_list)

    password = json.get('password', '')
    if not re_match(config['USER_PASSWORD_PATTERN'], password):
        return {'password': config['USER_PASSWORD_DESCRIPTION']}

    expired = bool(json.get('expired', False))

    if User.select().where(User.id == user_id).count() != 0:
        return {'id': '该用户ID %s 已经存在' % user_id}

    if User.select().where(User.name == name).count() != 0:
        return {'name': '该昵称 %s 已经存在' % name}

    new_user = User.create(id=user_id, name=name, permission=permission_value,
                           expired=expired, password=password)

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='User: Create',
        description='create user(%s).' % (user_id)
    )

    return None, {'user': new_user.to_dict()}


@bp.route('/user/', methods=['PATCH'])
@bp.route('/user/<id>', methods=['PATCH'])
@restful
@permission_require(Permission.MODIFY_USER)
def modify_user(id=None):
    """``PATCH`` |API_URL_BASE|/user/
    ``PATCH`` |API_URL_BASE|/user/:user_id

    Modify user information. User's role can't be modified.
    If no ``id`` was given then id will be automatically set to
    current user's id in this session.

    :param id: if not set, use ``current_user.get_id()``
    :param password: **JSON Param** plain password, without encoding
    :param boolean expired: **JSON Param**

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
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
            $errors: {
                permission: 'your are not allowed to change other user.',
                name: 'this name is invalid.',
                password: 'this password is invalid',
                name: 'this name is duplicated.',
                id: 'this id is duplicated.'
            }
        }

    Permission require:

        * ``MODIFY_USER``
        * ``MODIFY_OTHER_USER`` (if attempt to modify other user.)
    """
    json = request.get_json()

    id = id or current_user.get_id()
    if id != current_user.get_id() \
            and not current_user.can(Permission.MODIFY_OTHER_USER):
        return {'permission': 'Your are not allowed to change other user.'}

    name = json.get('name')
    if name and not re_match(app_config['USER_NAME_PATTERN'], name):
        return {'name': app_config['USER_NAME_DESCRIPTION']}

    password = json.get('password')
    if password \
            and not re_match(app_config['USER_PASSWORD_PATTERN'],
                             password):
        return {'password': app_config['USER_PASSWORD_DESCRIPTION']}

    expired = json.get('expired')

    if User.select().where(User.name == name).count() == 1:
        return {'name': '该昵称 %s 已存在' % name}

    try:
        this_user = User.get(User.id == id)
    except User.DoesNotExist:
        return {'id': '该用户ID %s 不存在' % id}

    if name:
        this_user.name = name

    if password:
        this_user.set_password(password)

    if expired:
        this_user.expired = bool(expired)

    # if nothing change, keep database unchanged
    if this_user.dirty_fields:
        this_user.save()

        signals.event_emitted.send(
            current_app._get_current_object(),
            type='User: Modify',
            description='modify properties %s of user(%s).' % (
                ','.join([f.name for f in this_user.dirty_fields]), id)
        )

    return None, {'user': this_user.to_dict()}


@bp.route('/user/<id>', methods=['DELETE'])
@permission_require(Permission.DELETE_USER)
@restful
def delete_user(id):
    """``DELETE`` |API_URL_BASE|/user/:user_id

    Delete a user. Superuser can't be deleted.

    :param id: user id

    Response JSON:

    .. code-block:: javascript

        // success
        {$errors: null}

        // failed
        {$errors: {id: 'this is user does not exist.'}}

    Permission require: ``DELETE_USER``
    """
    try:
        User.get(User.id == id).delete_instance()
    except User.DoesNotExist:
        return {'id': '该用户ID不存在'}

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='User: Delete',
        description='delete user(%s).' % id
    )

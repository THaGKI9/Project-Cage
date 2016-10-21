from re import match as re_match

from flask import request, current_app
from flask_login import current_user

from . import bp
from core import app_config
from core.models import Category, Permission
from core.helpers import restful, permission_require, signals


@bp.route('/categories/')
@restful
@permission_require(Permission.READ_CATEGORY)
def get_categories():
    """``GET`` |API_URL_BASE|/categories/

    Get a list of categories.

    :param order: **Query** supported key: *create_time(default)*,
        *article_count*, *name*
    :param boolean desc: **Query** decrease order, default: false

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            categories: [
                {
                    id: string,
                    name: string,
                    article_count: integer
                }
            ]
        }

    Permission: ``READ_CATEGORY``
    """
    supported_key = {
        'create_time': Category.create_time,
        'article_count': Category.article_count,
        'name': Category.name
    }
    default_key = supported_key['create_time']
    order_key = supported_key.get(request.args.get('order'), default_key)

    if request.args.get('desc', 'false') == 'true':
        order_key = order_key.desc()

    raw_categories = Category.select().order_by(order_key)
    categories = [category.to_dict() for category in raw_categories]
    return None, {'categories': categories}


@bp.route('/category/<id>')
@restful
@permission_require(Permission.READ_CATEGORY)
def get_a_category(id):
    """``GET`` |API_URL_BASE|/category/

    Get a category.

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            category: {
                id: string,
                name: string,
                article_count: integer
            ]
        }

    Permission: ``READ_CATEGORY``
    """
    try:
        category = Category.get(Category.id == id)
    except Category.DoesNotExist:
        return {'id': '该分类不存在'}
    return None, {'category': category.to_dict()}


@bp.route('/category/', methods=['POST'])
@restful
@permission_require(Permission.CREATE_CATEGORY)
def create_category():
    """``POST`` |API_URL_BASE|/category/

    Create a category.

    :param id: **JSON Param**, required
    :param name: **JSON Param**, required

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            category: {
                id: string,
                name: string,
                article_count: integer
            }
        }

        // failed
        {
            errors: {
                id: 'this id is invalid.',
                name: 'this name is invalid.',
                id: 'this id is duplicated.'
            }
        }

    Permission: ``CREATE_CATEGORY``
    """
    json = request.get_json()

    name = json.get('name', '').strip()
    if not name:
        return {'name': '请输入有效的分类名'}

    id = json.get('id', '')
    if not re_match(app_config['CATEGORY_ID_PATTERN'], id):
        return {'id': app_config['CATEGORY_ID_DESCRIPTION']}

    if Category.select().where(Category.id == id).count() == 1:
        return {'id': '该分类ID %s 已存在' % id}

    if Category.select().where(Category.name == name).count() == 1:
        return {'name': '该分类名 %s 已存在' % name}

    new_category = Category.create(id=id, name=name)

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='Category: Create',
        description='category(%s) has been create.' % new_category.id
    )

    return None, {'category': new_category.to_dict()}


@bp.route('/category/<id>', methods=['PATCH'])
@restful
@permission_require(Permission.EDIT_CATEGORY)
def edit_category(id):
    """``PATCH`` |API_URL_BASE|/category/<category id>

    Edit a category. Currently only support modify category name.

    :param name: **JSON Param**, required

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            category: {
                id: integer,
                name: string,
                article_count: integer
            }
        }

        // failed
        {
            errors: {
                permission: 'you are not allowed to modify category '
                            'created by other author',
                name: 'this name is invalid.'
            }
        }

    Permission:

        * ``EDIT_CATEGORY``
        * ``EDIT_OTHERS_CATEGORY`` (if attempt to edit
          category created by other.)
    """
    json = request.get_json()
    new_name = json.get('name', '').strip()
    if not new_name:
        return {'name': '请输入有效的分类名'}

    try:
        this_category = Category.get(Category.id == id)
    except Category.DoesNotExist:
        return {'id': '该分类 %s 不存在' % id}

    if this_category.create_by_id != current_user.get_id() \
            and not current_user.can(Permission.EDIT_OTHERS_CATEGORY):
        reason = ('You are not allowed to edit category '
                  'created by other author.')
        return {'permission': reason}

    old_name = this_category.name
    this_category.name = new_name
    this_category.save()

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='Category: Modify',
        description='category(%s) changed from `%s` to `%s`.' %
                    (id, old_name, new_name)
    )

    return None, {'category': this_category.to_dict()}


@bp.route('/category/<id>', methods=['DELETE'])
@restful
@permission_require(Permission.EDIT_CATEGORY)
def delete_category(id):
    """``DELETE`` |API_URL_BASE|/cate/<category id>

    Delete a category.

    :param id: category id

    Response JSON:

    .. code-block:: javascript

        // success
        {errors: null}

        // failed
        {
            errors: {
                permission: 'you are not allowed to delete category '
                            'created by other author',
                id: 'this category does not exist.'
            }
        }

    Permission:

        * ``EDIT_CATEGORY``
        * ``EDIT_OTHERS_CATEGORY`` (if attempt to delete
          category created by other.)
    """
    try:
        this_category = Category.get(Category.id == id)
    except Category.DoesNotExist:
        return {'id': '该分类 %s 不存在' % id}

    if this_category.create_by_id != current_user.get_id() \
            and not current_user.can(Permission.EDIT_OTHERS_CATEGORY):
        reason = ('You are not allowed to delete category '
                  'created by other author.')
        return {'permission': reason}

    this_category.delete_instance()

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='Category: Delete',
        description='category(%s) has been deleted.' % id
    )

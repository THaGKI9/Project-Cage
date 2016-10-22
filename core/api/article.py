from collections import OrderedDict
from re import match as re_match

from flask import current_app, request
from flask_login import current_user

from core import app_config
from core.helpers import (RendererCollection, permission_require, restful,
                          signals)
from core.helpers.signals import event_emitted
from core.models import Article, Category, Permission

from . import bp


@bp.route('/articles/')
@restful
@permission_require(Permission.READ_ARTICLE)
def get_articles():
    """``GET`` |API_URL_BASE|/articles/

    :param limit: **Query** limit amount of article per page,
        default: |ARTICLE_LIST_DEFAULT_LIMIT|
    :param page: **Query**  page control, start from: 0, default: 0
    :param category: **Query** id of category, optional
    :param order: **Query** supported key: *id*, *author*,
        *category*, *post_time(default)*, *read_count*, *text_type*,
        *title*, *update_time*
    :param boolean with_content: **Query**
    :param boolean desc: **Query** decrease order, default: false

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            articles: [
                {
                    id: string,
                    title: string,
                    author: { id: integer, name: string },
                    category: { id: string, name: string },
                    read_count: integer,
                    post_time: integer,
                    update_time: integer
                }
            ]
        }

    Permission: ``READ_ARTICLE``
    """
    supported_key = {
        'id': Article.id,
        'category': Article.category,
        'author': Article.author,
        'title': Article.title,
        'text_type': Article.text_type,
        'read_count': Article.read_count,
        'post_time': Article.post_time,
        'update_time': Article.update_time
    }

    default_key = supported_key['post_time']
    order_key = supported_key.get(request.args.get('order'), default_key)
    if request.args.get('desc', 'false') == 'true':
        order_key = order_key.desc()

    default_limit = app_config['ARTICLE_LIST_DEFAULT_LIMIT']
    limit = request.args.get('limit', default_limit, type=int)
    page = request.args.get('page', 0, type=int)
    category = request.args.get('category')
    with_content = request.args.get('with_content', 'false') == 'true'

    limit = default_limit if limit <= 0 else limit
    page = 0 if page <= 0 else page

    query = Article.query().order_by(order_key) \
                           .where(Article.public == True)  # noqa: E712

    if category:
        query = query.where(Article.category == category)

    query = query.offset(limit * page).limit(limit)

    return None, {'articles': [article.to_dict(with_content=with_content)
                               for article in query]}


@bp.route('/article/<id>')
@restful
@permission_require(Permission.READ_ARTICLE)
def get_an_article(id):
    """``GET`` |API_URL_BASE|/article/<article id>

    Get an article.

    :param boolean with_src: **Query** response with article source.
        need extra permission. default: false
    :param boolean with_content: **Query** response with article content.
        default: true

    Response JSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            article: {
                id: string,
                title: string,
                author: { id: integer, name: string },
                category: { id: string, name: string },
                content: string, // optional
                read_count: integer,
                post_time: integer,
                update_time: integer,
                text_type: string, // optional
                source_type: string // optional
            }
        }

        // failed
        {
            errors: {
                permission: 'you are not allowed to read the source.',
                permission: 'you are not allowed to read a private article',
                id: 'can not found this article. maybe it has
                     been been deleted.'
            }
        }

    Permission require:

        * ``READ_ARTICLE``
        * ``MODIFY_ARTICLE`` (if set **with_src** to ``true``)
    """
    with_content = request.args.get('with_content', 'true') == 'true'
    with_src = request.args.get('with_src', 'false') == 'true'

    if with_src and not current_user.can(Permission.EDIT_ARTICLE):
        return {'permission': 'You are not allowed to read the source.'}

    try:
        this_article = Article.query().where(Article.id == id).get()
    except Article.DoesNotExist:
        return {'id': '无法找到这篇文章，可能已经被删除'}

    if this_article.public is False \
            and this_article.author_id != current_user.get_id():
        return {'permission': '你无权查阅一片私密的文章'}

    return None, {'article': this_article.to_dict(with_src=with_src,
                                                  with_content=with_content)}


@bp.route('/article/', methods=['POST'])
@restful
@permission_require(Permission.POST_ARTICLE)
def post_article():
    """``POST`` |API_URL_BASE|/article/

    Post a new article.
    A private article doesn't belongs to any category.

    :param category: **JSON Param**
    :param id: **JSON Param**, article id
    :param title: **JSON Param**, article title
    :param text_type: **JSON Param**, text type should be supported, call
        :meth:`helpers.renderer.RendererCollection.get_supported_renderers`
        for list of supporting renderers.
    :param source_text: **JSON Param**
    :param boolean public: if set to false, ``category`` will be ignore anyone
        wouldn't read this article except the author. default: true
    :param boolean is_commentable: **JSON Param**, default: true

    ResponseJSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            article: {
                id: string,
                title: string,
                author: { id: integer, name: string },
                category: { id: string, name: string },
                read_count: integer,
                post_time: integer,
                update_time: integer
            }
        }

        // failed
        {
            errors: {
                category: 'a public article must belongs to a category.'
                category: 'this category does not exist.',
                id: 'this article id is invalid.',
                title: 'this title is invalid.',
                text_type: 'this type is not supported.'
                source_type: 'exception occurs when compile the text.'
            }
        }

    Permission require: ``POST_ARTICLE``
    """
    json = request.get_json()

    public = json.get('public') is not False
    if not public:
        category = None
    else:
        category = json.get('category')
        if category is None:
            return {'category': '公开的文章必须属于某一个分类'}
        if not Category.exist(Category.id == category):
            return {'category': '该分类不存在'}

    id = json.get('id', '')
    if not re_match(app_config['ARTICLE_ID_PATTERN'], id):
        return {'id': app_config['ARTICLE_ID_DESCRIPTION']}

    title = json.get('title', '').strip()
    if not title:
        return {'title': '请输入有效的文章标题'}

    text_type = json.get('text_type', '')
    if not RendererCollection.does_support(text_type):
        return {'text_type': '抱歉，暂不支持该格式的文章'}

    source_text = json.get('source_text', '')
    try:
        rendered_text = RendererCollection.render(text_type, source_text)
    except RendererCollection.RenderedError as ex:
        return {'source_text': '渲染文章失败，错误信息如下：\r\n' + ex.message}

    is_commentable = json.get('is_commentable') is not False

    article = Article.create(id=id, title=title,
                             text_type=text_type, source_text=source_text,
                             content=rendered_text,
                             is_commentable=is_commentable, public=public,
                             category=category)

    event_emitted.send(
        current_app._get_current_object(),
        type='Article: Post',
        description='Author(%s) posted a new article(%s).'
                    % (article.author_id, article.id)
    )

    return None, {'article': article.to_dict()}


@bp.route('/article/<id>', methods=['PATCH'])
@restful
@permission_require(Permission.POST_ARTICLE)
def edit_article(id):
    """``PATCH`` |API_URL_BASE|/article/<article id>

    Edit an article. ID and title are unchangable.

    :param category: **JSON Param**
    :param text_type: **JSON Param**, text type should be supported, call
        :meth:`helpers.renderer.RendererCollection.get_supported_renderers`
        for list of supporting renderers.
    :param source_text: **JSON Param**
    :param boolean public: if set to false, ``category`` will be ignore anyone
        wouldn't read this article except the author
    :param boolean is_commentable: **JSON Param**

    ResponseJSON:

    .. code-block:: javascript

        // success
        {
            errors: null,
            article: {
                id: string,
                title: string,
                author: { id: integer, name: string },
                category: { id: string, name: string },
                read_count: integer,
                post_time: integer,
                update_time: integer
            }
        }

        // failed
        {
            errors: {
                id: 'this article does not exist.',
                permission: 'your are not allowed to edit article
                             posted by other author'
                category: 'this category does not exist.',
                text_type: 'this type is not supported.',
                text_type: 'text type can not be changed individually.',
                source_type: 'exception occurs when compile the text.'
            }
        }

    Permission require:
        * ``EDIT_ARTICLE``
        * ``EDIT_OTHERS_ARTICLE`` (if attempt to edit article posted by
          other author.)
    """
    json = request.get_json()

    try:
        this_article = Article.get(Article.id == id)
    except Article.DoesNotExist:
        return {'id': '该文章不存在'}

    if this_article.author_id != current_user.get_id() \
            and not current_user.can(Permission.EDIT_OTHERS_ARTICLE):
        return {'permission': 'You are not allowed to edit article '
                              'posted by other author'}

    public = json.get('public')
    if not isinstance(public, bool):
        public = this_article.public

    this_article.public = public
    if not public:
        this_article.category = None
    else:
        category = json.get('category')
        if category is None and this_article.category is None:
            return {'category': '公开的文章必须属于某一个分类'}
        if category and category != this_article.category_id:
            if not Category.exist(Category.id == category):
                return {'category': '该分类不存在.'}
            else:
                this_article.category = category

    text_type = json.get('text_type')
    source_text = json.get('source_text')
    if text_type:
        if text_type != this_article.text_type and source_text is None:
            return {'text_type': '不能独立地修改文章格式'}
        if not RendererCollection.does_support(text_type):
            return {'text_type': '抱歉，暂不支持该格式的文章'}
        this_article.text_type = text_type

    if source_text:
        try:
            rendered_text = RendererCollection.render(this_article.text_type,
                                                      source_text)
        except RendererCollection.RenderedError as ex:
            return {'source_text': '渲染文章失败，错误信息如下：\r\n' + ex.message}
        this_article.source_text = source_text
        this_article.content = rendered_text

    this_article.is_commentable = json.get('is_commentable', True)
    this_article.save()

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='User: Edit',
        description='edit properties %s of article(%s).'
                    % (','.join([f.name for f in this_article.dirty_fields]),
                       id)
    )

    return None, {'article': this_article.to_dict()}


@bp.route('/article/<id>', methods=['DELETE'])
@restful
@permission_require(Permission.EDIT_ARTICLE)
def delete_article(id):
    """``DELETE`` |API_URL_BASE|/article/<article id>

    Delete an article.

    Response JSON:

    .. code-block:: javascript

        // success
        {errors: null}

        // failed
        {
            errors: {
                permission: 'you are not allowed to delete article
                             posted by other author.',
                id: 'can not find this article. maybe it has been deleted.'
            }
        }

    Permission require:

        * ``EDIT_ARTICLE``
        * ``EDIT_OTHERS_ARTICLE`` (if attempt to delete article posted by
          other author.)
    """
    try:
        this_article = Article.get(Article.id == id)
    except Article.DoesNotExist:
        return {'id': '无法找到该文章，可能已经被删除'}

    if this_article.author != current_user.get_id() and \
            not current_user.can(Permission.EDIT_OTHERS_ARTICLE):
        return {'permission': 'You are not allowed to delete article'
                              'posted by other author.'}

    this_article.delete_instance()

    signals.event_emitted.send(
        current_app._get_current_object(),
        type='Article: Delete',
        description='article(%s) has been deleted by %s.'
                    % (id, current_user.get_id())
    )


@bp.route('/article-type/')
@restful
@permission_require(Permission.POST_ARTICLE)
def get_article_types():
    """``GET`` |API_URL_BASE|/article-type/

    Get the list of supporting article types.

    Response:

    .. code-block:: javascript

        {
            errors: null,
            types: [
                {
                    ext: 'extension',
                    name: 'name',
                    description: 'description of article type.'
                }
            ]
        }

    Permission require: ``POST_ARTICLE``
    """
    rv_list = []
    for renderer in RendererCollection.get_supported_renderers():
        type_dict = OrderedDict()
        type_dict['ext'] = renderer['ext']
        type_dict['name'] = renderer['name']
        type_dict['description'] = renderer['description']
        rv_list.append(type_dict)

    return None, {'types': rv_list}

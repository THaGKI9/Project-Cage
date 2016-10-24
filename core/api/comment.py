from flask import request, current_app
from flask_login import current_user

from core import app_config
from core.helpers import restful, permission_require
from core.models import Article, Comment, Permission
from core.helpers.signals import event_emitted

from . import bp


@bp.route('/article/<aid>/comments/')
@restful
@permission_require(Permission.READ_COMMENT)
def get_comments(aid):
    '''``GET`` |API_URL_BASE|/article/:aid/comments/

    Get information of all comments to an article.

    :param limit: **Query** limit amount of comment per page,
        default: |COMMENT_LIST_DEFAULT_LIMIT|
    :param page: **Query**  page control, start from zero, default: 1

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            comments: [
                {
                    id: integer,
                    nickname: string,
                    content: string,
                    time: datetime,
                    reply_to: integer // maybe null if no references.
                }
            ]
        }

        // failed
        {$errors: {article_id: 'this article doesn't not exist.'}}

    Permission required: ``READ_COMMENT``
    '''
    default_limit = app_config['COMMENT_LIST_DEFAULT_LIMIT']

    try:
        author_id = (Article.select(Article.author)
                            .where(Article.id == aid).get()).author_id
    except Article.DoesNotExist:
        return {'article_id': '无法找到这篇文章，可能已经被删除'}

    page = request.args.get('page', 1, type=int) - 1
    limit = request.args.get('limit', default_limit, type=int)

    query = (Comment.select()
                    .where(Comment.article == aid)
                    .offset(page * limit).limit(limit + 1))

    if current_user.get_id() != author_id:
        query = query.where(Comment.reviewed == True)  # noqa: E712

    comments = [comment.to_dict() for comment in query]
    is_more = len(comments) > limit

    return None, {'is_more': is_more, 'comments': comments[:limit]}


@bp.route('/article/<aid>/comment/<int:cid>')
@restful
@permission_require(Permission.READ_COMMENT)
def get_a_comment(aid, cid):
    '''``GET`` |API_URL_BASE|/article/:aid/comment/:cid

    Get a comment to an article

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            comment: {
                id: integer,
                nickname: string,
                content: string,
                time: datetime,
                reply_to: integer // maybe null if no references.
            }
        }

        // failed
        {$errors: {comment_id: 'this comment does not exist.'}}

    Permission required: ``READ_COMMENT``
    '''
    try:
        author_id = (Article.select(Article.author)
                            .where(Article.id == aid).get()).author_id
        comment = Comment.get((Comment.id == cid) & (Comment.article == aid))

        if comment.reviewed is False and current_user.get_id() != author_id:
            raise Comment.DoesNotExist()
    except (Article.DoesNotExist, Comment.DoesNotExist):
        return {'comment_id': '该评论不存在'}

    return None, {'comment': comment.to_dict()}


@bp.route('/article/<aid>/comment/', methods=['POST'])
@bp.route('/article/<aid>/comment/<int:reply_to_cid>', methods=['POST'])
@restful
@permission_require(Permission.WRITE_COMMENT)
def write_comment(aid, reply_to_cid=None):
    '''``POST`` |API_URL_BASE|/article/:aid/comment/
    ``POST`` |API_URL_BASE|/article/:aid/comment/:cid

    Write a comment to an article.

    :param nickname: **JSON Param** this argument will be ignored
        when current user is authenticated
    :param content: **JSON Param** required

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            comment: {
                id: integer,
                nickname: string,
                content: string,
                time: datetime,
                reply_to: integer // maybe null if no references.
            }
        }

        // failed
        {
            $errors: {
                comment_id: 'the comment you reply to doesn't not exist.'
                nickname: 'this nickname is illegal',
                content: 'this content is illegal.'
            }
        }

    Permission required: ``WRITE_COMMENT``
    '''
    json = request.get_json()

    try:
        author_id = (Article.select(Article.author)
                            .where(Article.id == aid).get()).author_id
        reply_to = reply_to_cid
        if reply_to is not None:
            if not Comment.exist((Comment.article == aid)
                                 & (Comment.id == reply_to)):
                raise Comment.DoesNotExist()
    except (Article.DoesNotExist, Comment.DoesNotExist):
        return {'comment_id': '欲回复的评论不存在'}

    is_author = author_id == current_user.get_id()

    if is_author:
        nickname = current_user.name
    else:
        nickname = json.get('nickname') or ''
        nickname = nickname.strip()
        if not nickname:
            return {'nickname': '请输入有效的昵称'}

    content = json.get('content') or ''
    content = content.strip()
    if not content:
        return {'content': '请输入有效的内容'}

    reviewed = is_author or not app_config['COMMENT_NEED_REVIEW']

    comment = Comment.create(article=aid, content=content,
                             nickname=nickname, reviewed=reviewed,
                             is_author=is_author, reply_to=reply_to)

    event_emitted.send(
        current_app._get_current_object(),
        type='Comment: Create',
        description='new comment(%d) in article(%s) has been added.' %
                    (comment.id, aid)
    )

    return None, {'comment': comment.to_dict()}


@bp.route('/article/<aid>/comment/<int:cid>', methods=['PATCH'])
@restful
@permission_require(Permission.REVIEW_COMMENT)
def review_comment(aid, cid):
    '''``PATCH`` |API_URL_BASE|/article/:aid/comment/:cid

    Review a comment. The author is the only one having permission.

    Response JSON:

    .. code-block:: javascript

        // success
        {
            $errors: null,
            comment: {
                id: integer,
                nickname: string,
                content: string,
                time: datetime,
                reply_to: integer // maybe null if no references.
            }
        }

        // failed
        {$errors: {reply_to: 'the comment you reply to doesn't not exist.'}}

    Permission required: ``REVIEW_COMMENT``
    '''
    try:
        author_id = (Article.select(Article.author)
                            .where(Article.id == aid).get()).author_id
        comment = Comment.get((Comment.id == cid) & (Comment.article == aid))
        if not author_id == current_user.get_id():
            raise Comment.DoesNotExist()
    except (Article.DoesNotExist, Comment.DoesNotExist):
        return {'comment_id': '欲回复的评论不存在'}

    comment.reviewed = True
    comment.save()

    event_emitted.send(
        current_app._get_current_object(),
        type='Comment: Review',
        description='comment(%d) has been reviewed by %s.' %
                    (comment.id, current_user.get_id())
    )

    return None, {'comment': comment.to_dict()}


@bp.route('/article/<aid>/comment/<int:cid>', methods=['DELETE'])
@restful
@permission_require(Permission.REVIEW_COMMENT)
def delete_comment(aid, cid):
    '''``DELETE`` |API_URL_BASE|/article/:aid/comment/:cid

    Delete a comment. The author is the only one having permission.

    Response JSON:

    .. code-block:: javascript

        // success
        {$errors: null}

        // failed
        {
            $errors: {
                comment_id: 'the comment you reply to doesn't not exist.'
                permission: 'you are not allowed to delete this comment.'
            }
        }

    Permission required: ``REVIEW_COMMENT``
    '''
    try:
        author_id = (Article.select(Article.author)
                            .where(Article.id == aid).get()).author_id
        comment = Comment.get((Comment.id == cid) & (Comment.article == aid))
    except (Article.DoesNotExist, Comment.DoesNotExist):
        return {'comment_id': '该评论不存在'}

    is_author = author_id == current_user.get_id()
    if not is_author:
        return {'permission': '你无权删除该条评论'}

    comment.delete_instance()

    event_emitted.send(
        current_app._get_current_object(),
        type='Comment: Delete',
        description='comment(%d) has been deleted by %s.' %
                    (comment.id, current_user.get_id())
    )

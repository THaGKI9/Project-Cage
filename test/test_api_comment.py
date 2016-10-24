from json import dumps as json_dumps

from core.models import Comment, Article
from test import BaseTestCase


class ApiCommentTestCase(BaseTestCase):
    art = Article

    def setUp(self):
        self.reset_database()
        self.enable_comment_review(True)
        self.logout()
        self.login_as_author()

        with self.app.test_request_context():
            self.art = Article.create(id='testart', title='',
                                      text_type='', source_text='',
                                      author='author')
        self.path_prefix = self.api_url_base + '/article/' + self.art.id

    def insert_a_comment(self, reviewed=False):
        with self.app.test_request_context():
            return Comment.create(article=self.art, reviewed=reviewed,
                                  content='', nickname='')

    def enable_comment_review(self, status):
        with self.ctx:
            self.app.config['COMMENT_NEED_REVIEW'] = status

    def get_a_comment(self, comment_id):
        return self.client.get(self.path_prefix
                               + '/comment/' + str(comment_id))

    def test_get_comments(self):
        insert_amount = 30
        with self.app.test_request_context(), self.db.atomic():
            coms = [dict(content='comment_test', article=self.art,
                         nickname='tester', reviewed=True)
                    for i in range(insert_amount)]
            Comment.insert_many(coms).execute()

        resp = self.client.get(self.path_prefix + '/comments/',
                               query_string={'limit': insert_amount // 2})
        self.assertResponseRestfulAndSuccess(resp)
        self.assertEqual(insert_amount // 2,
                         len(self.get_json(resp)['comments']))

    def test_get_comments_include_unreviewed(self):
        insert_amount = 30
        with self.app.test_request_context(), self.db.atomic():
            coms = [dict(content='comment_test_re', article=self.art,
                         nickname='tester', reviewed=True)
                    for i in range(insert_amount)]
            Comment.insert_many(coms).execute()
            coms = [dict(content='comment_test_unre', article=self.art,
                         nickname='tester')
                    for i in range(insert_amount)]
            Comment.insert_many(coms).execute()

        resp = self.client.get(self.path_prefix + '/comments/',
                               query_string={'limit': insert_amount * 2})
        self.assertResponseRestfulAndSuccess(resp)
        self.assertEqual(insert_amount * 2,
                         len(self.get_json(resp)['comments']))

    def test_get_reviewed_comments_among_unreviewed_comments(self):
        insert_amount = 30
        with self.app.test_request_context(), self.db.atomic():
            coms = [dict(content='comment_test_re', article=self.art,
                         nickname='tester', reviewed=True)
                    for i in range(insert_amount)]
            Comment.insert_many(coms).execute()
            coms = [dict(content='comment_test_unre', article=self.art,
                         nickname='tester')
                    for i in range(insert_amount)]
            Comment.insert_many(coms).execute()

        self.logout()
        resp = self.client.get(self.path_prefix + '/comments/',
                               query_string={'limit': insert_amount * 2})
        self.assertResponseRestfulAndSuccess(resp)
        self.assertEqual(insert_amount,
                         len(self.get_json(resp)['comments']))

    def test_get_comments_to_non_exist_article(self):
        resp = self.client.get(self.api_url_base + '/article/' +
                               'fake-article' + '/comments/')
        self.assertResponseErrorInField(resp, 'article_id')

    def test_get_a_unreviewed_comment(self):
        with self.app.test_request_context(), self.db.atomic():
            comment = Comment.create(content='comment_test', article=self.art,
                                     nickname='tester', reviewed=False)

        resp = self.get_a_comment(comment.id)
        self.assertResponseRestfulAndSuccess(resp)

        self.assertJSONHasKey(resp, 'comment')
        comment_ = self.get_json(resp)['comment']

        self.assertEqual(comment_['content'], comment.content)

    def test_get_a_unreviewed_comment_without_permission(self):
        with self.app.test_request_context(), self.db.atomic():
            comment = Comment.create(content='comment_test', article=self.art,
                                     nickname='tester', reviewed=False)

        self.login_as_su()
        resp = self.get_a_comment(comment.id)
        self.assertResponseErrorInField(resp, 'comment_id')

    def test_get_a_comment_mismatch_article(self):
        with self.app.test_request_context(), self.db.atomic():
            article = Article.create(id='testart_', title='',
                                     text_type='', source_text='')
            comment = Comment.create(content='comment_test', article=self.art,
                                     nickname='tester', reviewed=True)

        resp = self.client.get(self.api_url_base + '/article/' + article.id
                               + '/comment/' + str(comment.id))
        self.assertResponseErrorInField(resp, 'comment_id')

    def test_write_a_comment_as_author(self):
        payload = {'nickname': 'author_test', 'content': 'test comment'}

        resp = self.client.post(self.path_prefix + '/comment/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(resp, 'comment')

        resp = self.get_a_comment(self.get_json(resp)['comment']['id'])
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(resp, 'comment')

        comment = self.get_json(resp)['comment']
        self.assertEqual('作者', comment['nickname'])
        self.assertEqual(payload['content'], comment['content'])

    def test_write_a_comment_as_reader(self):
        self.logout()
        self.enable_comment_review(False)
        payload = {'nickname': 'author_test', 'content': 'test comment'}

        resp = self.client.post(self.path_prefix + '/comment/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(resp, 'comment')

        resp = self.get_a_comment(self.get_json(resp)['comment']['id'])
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(resp, 'comment')

        comment = self.get_json(resp)['comment']
        self.assertEqual(payload['nickname'], comment['nickname'])
        self.assertEqual(payload['content'], comment['content'])

    def test_write_a_comment_with_illegal_nickname(self):
        self.logout()
        payload = {'nickname': '', 'content': 'test comment'}

        resp = self.client.post(self.path_prefix + '/comment/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'nickname')

    def test_write_a_comment_with_illegal_content(self):
        payload = {'nickname': 'author_test', 'content': ''}

        resp = self.client.post(self.path_prefix + '/comment/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'content')

    def test_write_a_comment_reply_to_a_comment(self):
        payload = {'nickname': 'author_test', 'content': 'test comment'}

        comment = self.insert_a_comment()
        resp = self.client.post(self.path_prefix
                                + '/comment/' + str(comment.id),
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(resp, 'comment')
        comment_ = self.get_json(resp)['comment']

        resp = self.get_a_comment(comment_['id'])
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(resp, 'comment')
        comment_ = self.get_json(resp)['comment']
        self.assertJSONHasKey(comment_, 'reply_to')
        self.assertEqual(comment.id, comment_['reply_to'])

    def test_write_a_comment_reply_to_a_comment_with_illegal_nickname(self):
        self.logout()
        payload = {'nickname': '', 'content': 'test comment'}

        comment = self.insert_a_comment()
        resp = self.client.post(self.path_prefix
                                + '/comment/' + str(comment.id),
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'nickname')

    def test_write_a_comment_reply_to_a_comment_with_illegal_content(self):
        payload = {'nickname': 'author_test', 'content': ''}

        comment = self.insert_a_comment()
        resp = self.client.post(self.path_prefix
                                + '/comment/' + str(comment.id),
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'content')

    def test_write_a_comment_reply_to_a_non_exist_comment(self):
        payload = {'nickname': 'author_test', 'content': 'test comment'}

        resp = self.client.post(self.path_prefix
                                + '/comment/' + '10010',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'comment_id')

    def test_write_a_comment_reply_to_mismatch_article_comment(self):
        with self.app.test_request_context(), self.db.atomic():
            article = Article.create(id='testart_', title='',
                                     text_type='', source_text='')

        payload = {'nickname': 'author_test', 'content': 'test comment'}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id
                                 + '/comment/' + '10010',
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'comment_id')

    def test_review_a_comment(self):
        self.logout()
        comment = self.insert_a_comment()
        resp = self.get_a_comment(comment.id)
        self.assertResponseErrorInField(resp, 'comment_id')

        self.login_as_author()
        resp = self.client.patch(self.path_prefix
                                 + '/comment/' + str(comment.id))
        self.assertResponseRestfulAndSuccess(resp)

        self.logout()
        resp = self.get_a_comment(comment.id)
        json = self.get_json(resp)
        self.assertResponseRestfulAndSuccess(resp)
        self.assertJSONHasKey(json, 'comment')
        self.assertEqual(comment.content, json['comment']['content'])

    def test_review_a_comment_without_permission(self):
        self.logout()
        self.login_as_su()
        comment = self.insert_a_comment()

        resp = self.client.patch(self.path_prefix
                                 + '/comment/' + str(comment.id))
        self.assertResponseErrorInField(resp, 'comment_id')

    def test_delete_a_comment(self):
        comment = self.insert_a_comment()
        resp = self.client.delete(self.path_prefix
                                  + '/comment/' + str(comment.id))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_a_comment(comment.id)
        self.assertResponseErrorInField(resp, 'comment_id')

    def test_delete_a_comment_without_permission(self):
        comment = self.insert_a_comment()

        self.logout()
        self.login_as_su()
        resp = self.client.delete(self.path_prefix
                                  + '/comment/' + str(comment.id))
        self.assertResponseErrorInField(resp, 'permission')

    def test_delete_a_non_exist_comment(self):
        resp = self.client.delete(self.path_prefix
                                  + '/comment/' + '1111')
        self.assertResponseErrorInField(resp, 'comment_id')

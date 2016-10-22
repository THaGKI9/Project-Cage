from json import dumps as json_dumps

from core.models import Article, Category
from test import BaseTestCase


class ApiArticleTestCase(BaseTestCase):
    def setUp(self):
        self.reset_database()
        self.logout()

    def insert_a_category(self):
        with self.app.test_request_context():
            return Category.create(id='testcate', name='testcate').id

    def post_an_article(self, public=True, author=None):
        with self.app.test_request_context():
            cate = self.insert_a_category() if public else None
            return Article.create(id='testarticle', title='testarticle',
                                  text_type='md', source_text='# hello world',
                                  is_commentable='false', public=public,
                                  category=cate, author=author)

    def get_an_article(self, id):
        return self.client.get(self.api_url_base + '/article/' + id)

    def test_get_articles(self):
        insert_amount = 30
        with self.app.test_request_context(), self.db.atomic():
            prefix = 'testarticle'
            articles = [dict(id=prefix + str(i), title=prefix,
                             text_type=prefix, source_text=prefix)
                        for i in range(insert_amount)]
            Article.insert_many(articles).execute()

        resp = self.client.get(self.api_url_base + '/articles/',
                               query_string={'limit': insert_amount})
        self.assertResponseRestful(resp)

        articles = self.get_json(resp)['articles']
        self.assertEqual(len(articles), insert_amount)

    def test_get_articles_without_private_article(self):
        insert_amount = 30
        with self.app.test_request_context(), self.db.atomic():
            prefix = 'testarticle'
            articles = [dict(id=prefix + str(i), title=prefix,
                             text_type=prefix, source_text=prefix)
                        for i in range(insert_amount)]
            Article.insert_many(articles).execute()
            prefix = 'testarticle-p'
            articles = [dict(id=prefix + str(i), title=prefix,
                             text_type=prefix, source_text=prefix,
                             public=False)
                        for i in range(insert_amount)]
            Article.insert_many(articles).execute()

        resp = self.client.get(self.api_url_base + '/articles/',
                               query_string={'limit': insert_amount * 2})
        self.assertResponseRestful(resp)

        articles = self.get_json(resp)['articles']
        self.assertEqual(len(articles), insert_amount)

    def test_get_articles_order_by_id_desc(self):
        insert_amount = 30
        with self.app.test_request_context(), self.db.atomic():
            prefix = 'testarticle'
            articles = [dict(id=prefix + str(i), title=prefix,
                             text_type=prefix, source_text=prefix)
                        for i in range(insert_amount)]
            Article.insert_many(articles).execute()

        resp = self.client.get(self.api_url_base + '/articles/',
                               query_string={'limit': insert_amount,
                                             'order': 'id',
                                             'desc': 'true'})
        self.assertResponseRestful(resp)

        expected_ids = sorted([article['id'] for article in articles],
                              reverse=True)
        result_ids = [article['id']
                      for article in self.get_json(resp)['articles']]
        self.assertListEqual(expected_ids, result_ids)

    def test_get_articles_filter_by_category(self):
        from random import choice
        insert_amount_per_cate = 30
        category_amount = 3
        cate_prefix = 'cate'
        article_prefix = 'art'
        with self.app.test_request_context(), self.db.atomic():
            cates = [dict(id=cate_prefix + str(i),
                          name=cate_prefix + str(i))
                     for i in range(category_amount)]
            Category.insert_many(cates).execute()

            cate_to_insert = choice(cates)['id']

            articles = [dict(id=article_prefix + str(i), title=article_prefix,
                             text_type=article_prefix,
                             source_text=article_prefix,
                             category=cate_to_insert)
                        for i in range(insert_amount_per_cate)]
            Article.insert_many(articles).execute()

        resp = self.client.get(self.api_url_base + '/articles/',
                               query_string={'limit': insert_amount_per_cate,
                                             'category': cate_to_insert})
        self.assertResponseRestful(resp)

        articles = self.get_json(resp)['articles']
        self.assertEqual(len(articles), insert_amount_per_cate)
        for article in articles:
            self.assertEqual(article['category']['id'], cate_to_insert)

    def test_get_articles_filter_by_nonexist_category(self):
        from random import choice
        insert_amount_per_cate = 30
        category_amount = 3
        cate_prefix = 'cate'
        article_prefix = 'art'
        with self.app.test_request_context(), self.db.atomic():
            cates = [dict(id=cate_prefix + str(i),
                          name=cate_prefix + str(i))
                     for i in range(category_amount)]
            Category.insert_many(cates).execute()

            cate_to_insert = choice(cates)['id']

            articles = [dict(id=article_prefix + str(i), title=article_prefix,
                             text_type=article_prefix,
                             source_text=article_prefix,
                             category=cate_to_insert)
                        for i in range(insert_amount_per_cate)]
            Article.insert_many(articles).execute()

        resp = self.client.get(self.api_url_base + '/articles/',
                               query_string={'limit': insert_amount_per_cate,
                                             'category': cate_to_insert + '_'})
        self.assertResponseRestful(resp)

        articles = self.get_json(resp)['articles']
        self.assertEqual(len(articles), 0)

    def test_get_an_article(self):
        with self.app.test_request_context():
            article = Article.create(id='testart', title='testart',
                                     text_type='md', source_text='# hello',
                                     is_commentable=False)

        resp = self.client.get(self.api_url_base + '/article/' + article.id)
        self.assertResponseRestfulAndSuccess(resp)

        result_article = self.get_json(resp)['article']
        self.assertEqual(result_article['id'], article.id)
        self.assertEqual(result_article['title'], article.title)
        self.assertEqual(result_article['is_commentable'],
                         article.is_commentable)

    def test_get_a_private_article(self):
        self.login_as_author()
        with self.app.test_request_context():
            article = Article.create(id='testart', title='testart',
                                     text_type='md', source_text='# hello',
                                     is_commentable=False, author='author',
                                     public=False)

        resp = self.client.get(self.api_url_base + '/article/' + article.id)
        self.assertResponseRestfulAndSuccess(resp)

        result_article = self.get_json(resp)['article']
        self.assertEqual(result_article['id'], article.id)

    def test_get_a_private_article_without_permission(self):
        self.login_as_author()
        with self.app.test_request_context():
            article = Article.create(id='testart', title='testart',
                                     text_type='md', source_text='# hello',
                                     is_commentable=False, public=False)

        self.logout()
        self.login_as_su()
        resp = self.client.get(self.api_url_base + '/article/' + article.id)
        self.assertResponseErrorInField(resp, 'permission')

    def test_get_an_article_src(self):
        with self.app.test_request_context():
            article = Article.create(id='testart', title='testart',
                                     text_type='md', source_text='# hello',
                                     is_commentable=False)

        self.login_as_su()
        resp = self.client.get(self.api_url_base + '/article/' + article.id,
                               query_string={'with_src': 'true'})
        self.assertResponseRestfulAndSuccess(resp)

        result_article = self.get_json(resp)['article']
        self.assertEqual(result_article['id'], article.id)
        self.assertIn('text_type', result_article)
        self.assertIn('source_text', result_article)

    def test_get_an_article_src_without_permission(self):
        with self.app.test_request_context():
            article = Article.create(id='testart', title='testart',
                                     text_type='md', source_text='# hello',
                                     is_commentable=False)

        resp = self.client.get(self.api_url_base + '/article/' + article.id,
                               query_string={'with_src': 'true'})
        self.assertResponseErrorInField(resp, 'permission')

    def test_get_a_non_exist_article(self):
        resp = self.client.get(self.api_url_base + '/article/' + 'fakeid')
        self.assertResponseErrorInField(resp, 'id')

    def test_post_an_article(self):
        payload = {
            'id': 'testarticle',
            'title': 'testarticle',
            'text_type': 'md',
            'source_text': '# hello world',
            'category': self.insert_a_category()
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(payload['id'])
        self.assertResponseRestfulAndSuccess(resp)

    def test_post_an_article_uncommentable(self):
        payload = {
            'id': 'testarticle',
            'title': 'testarticle',
            'text_type': 'md',
            'source_text': '# hello world',
            'is_commentable': False,
            'category': self.insert_a_category()
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(payload['id'])
        self.assertResponseRestfulAndSuccess(resp)
        self.assertEqual(self.get_json(resp)['article']['is_commentable'],
                         False)

    def test_post_an_article_with_illegal_id(self):
        payload = {
            'id': 'test.article',
            'title': 'testarticle',
            'text_type': 'md',
            'source_text': '# hello world',
            'is_commentable': 'false',
            'category': self.insert_a_category()
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'id')

    def test_post_an_article_with_illegal_title(self):
        payload = {
            'id': 'testarticle',
            'title': '',
            'text_type': 'md',
            'source_text': '# hello world',
            'is_commentable': 'false',
            'category': self.insert_a_category()
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'title')

    def test_post_a_private_article(self):
        payload = {
            'id': 'testarticle',
            'title': 'testarticle',
            'text_type': 'md',
            'source_text': '# hello world',
            'is_commentable': 'false',
            'category': self.insert_a_category(),
            'public': False
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(payload['id'])
        self.assertResponseRestfulAndSuccess(resp)
        article = self.get_json(resp)['article']
        self.assertEqual(payload['public'], article['public'])

    def test_post_a_public_article_with_no_category(self):
        payload = {
            'id': 'testarticle',
            'title': 'testarticle',
            'text_type': 'md',
            'source_text': '# hello world',
            'is_commentable': 'false'
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'category')

    def test_post_an_article_with_non_exist_category(self):
        payload = {
            'id': 'testarticle',
            'title': 'testarticle',
            'text_type': 'md',
            'source_text': '# hello world',
            'is_commentable': 'false',
            'category': 'fake-cate'
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'category')

    def test_post_an_article_with_unsupported_type(self):
        payload = {
            'id': 'testarticle',
            'title': 'testarticle',
            'text_type': 'what type?',
            'source_text': '# hello world',
            'is_commentable': 'false',
            'category': self.insert_a_category()
        }

        resp = self.client.post(self.api_url_base + '/article/',
                                content_type='application/json',
                                data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'text_type')

    def test_edit_an_article(self):
        self.login_as_su()
        article = self.post_an_article()

        payload = {'text_type': 'md',
                   'source_text': '# Hello New'}

        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(article.id)
        article = self.get_json(resp)['article']
        self.assertEqual(article['content'], '<h1>Hello New</h1>')

    def test_edit_an_article_commentable_property(self):
        self.login_as_su()
        article = self.post_an_article()

        payload = {'is_commentable': False}

        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(article.id)
        article = self.get_json(resp)['article']
        self.assertEqual(article['is_commentable'],
                         payload['is_commentable'])

    def test_edit_a_non_exist_article(self):
        article_id = 'fake-id'
        payload = {'source_text': '# Hello new world',
                   'is_commentable': False}

        resp = self.client.patch(self.api_url_base + '/article/' + article_id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'id')

    def test_edit_an_article_posted_by_other_author_without_permission(self):
        self.login_as_su()
        article = self.post_an_article()

        self.logout()
        self.login_as_author()

        payload = {'source_text': '# Hello new world',
                   'is_commentable': False}

        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'permission')

    def test_edit_an_article_to_non_exist_category(self):
        self.login_as_su()
        article = self.post_an_article()

        payload = {'category': 'fake-cate'}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'category')

    def test_edit_an_article_to_an_new_category(self):
        self.login_as_su()
        article = self.post_an_article()
        with self.app.test_request_context():
            category = Category.create(id='new-cate', name='testcatenew')

        payload = {'category': category.id}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(article.id)
        article = self.get_json(resp)['article']
        self.assertEqual(article['category']['id'], category.id)

    def test_edit_an_article_to_private_status(self):
        article = self.post_an_article()

        payload = {'public': False}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(article.id)
        self.assertResponseRestfulAndSuccess(resp)
        article = self.get_json(resp)['article']
        self.assertNotIn('category', article)

    def test_edit_an_article_to_public_status_with_no_category(self):
        self.login_as_su()
        article = self.post_an_article(public=False)

        payload = {'public': True}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'category')

    def test_edit_an_article_text_type_individually(self):
        self.login_as_su()
        article = self.post_an_article()

        payload = {'text_type': 'rst'}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'text_type')

    def test_edit_an_article_to_unsupported_text_type(self):
        self.login_as_su()
        article = self.post_an_article()

        payload = {'text_type': 'rst', 'source_text': 'hello'}
        resp = self.client.patch(self.api_url_base + '/article/' + article.id,
                                 content_type='application/json',
                                 data=json_dumps(payload))
        self.assertResponseErrorInField(resp, 'text_type')

    def test_delete_an_article(self):
        self.login_as_su()
        article = self.post_an_article()

        resp = self.client.delete(self.api_url_base + '/article/' + article.id,
                                  content_type='application/json')
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(article.id)
        self.assertResponseErrorInField(resp, 'id')

    def test_delete_an_article_posted_by_other_author(self):
        self.login_as_author()
        article = self.post_an_article()

        self.logout()
        self.login_as_su()
        resp = self.client.delete(self.api_url_base + '/article/' + article.id,
                                  content_type='application/json')
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_an_article(article.id)
        self.assertResponseErrorInField(resp, 'id')

    def test_delete_an_article_posted_by_other_author_without_permission(self):
        self.login_as_su()
        article = self.post_an_article()

        self.logout()
        self.login_as_author()
        resp = self.client.delete(self.api_url_base + '/article/' + article.id,
                                  content_type='application/json')
        self.assertResponseErrorInField(resp, 'permission')

    def test_delete_a_non_exist_article(self):
        article_id = 'fake-id'
        resp = self.client.delete(self.api_url_base + '/article/' + article_id,
                                  content_type='application/json')
        self.assertResponseErrorInField(resp, 'id')

    def test_get_article_types(self):
        resp = self.client.get(self.api_url_base + '/article-type/')
        self.assertResponseRestfulAndSuccess(resp)
        self.assertIn('types', self.get_json(resp))

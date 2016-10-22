from json import dumps as json_dumps

from core.models import Article, Category
from test import BaseTestCase


class ApiCategoryTestCase(BaseTestCase):
    def setUp(self):
        self.reset_database()

    def get_category(self, id):
        return self.client.get(self.api_url_base + '/category/' + id)

    def test_get_cates(self):
        insert_amount = 30
        prefix = 'testcate'
        with self.app.test_request_context(), self.db.atomic():
            cates = [dict(id=prefix + str(i), name=prefix + str(i))
                     for i in range(insert_amount)]
            Category.insert_many(cates).execute()

        resp = self.client.get(self.api_url_base + '/categories/')
        self.assertResponseRestfulAndSuccess(resp)

        categories = self.get_json(resp)['categories']
        self.assertEqual(len(categories), insert_amount)
        nums = [int(cate['name'][len(prefix):]) for cate in categories]
        self.assertListEqual(nums, list(range(insert_amount)))

    def test_get_cates_desc(self):
        insert_amount = 30
        prefix = 'testcate'
        with self.app.test_request_context(), self.db.atomic():
            cates = [dict(id=prefix + str(i), name=prefix + str(i))
                     for i in range(insert_amount)]
            Category.insert_many(cates).execute()

        resp = self.client.get(self.api_url_base + '/categories/?desc=true')
        self.assertResponseRestfulAndSuccess(resp)

        categories = self.get_json(resp)['categories']
        self.assertEqual(len(categories), insert_amount)

        nums = [int(cate['name'][len(prefix):]) for cate in categories][::-1]
        self.assertListEqual(nums, list(range(insert_amount)))

    def test_get_cates_order_by_article_count(self):
        insert_amount = 10
        prefix = 'testcate'

        with self.app.test_request_context(), self.db.atomic():
            cates = [dict(id=prefix + str(i), name=prefix + str(i))
                     for i in range(insert_amount)]

            Category.insert_many(cates).execute()

            for index, cate in enumerate(cates):
                articles = [dict(id=str(index) + str(i), title='hello',
                                 text_type='md', source_text='# hello',
                                 category=cate['id'])
                            for i in range((index + 1) * 2)]

                Article.insert_many(articles).execute()

        resp = self.client.get(self.api_url_base + '/categories/',
                               query_string={'order': 'article_count',
                                             'desc': 'true'})
        self.assertResponseRestfulAndSuccess(resp)
        categories = self.get_json(resp)['categories']
        result_counts = [cate['article_count'] for cate in categories]
        expected_counts = sorted(result_counts, reverse=True)
        self.assertListEqual(result_counts, expected_counts)

    def test_create_cate(self):
        payload_json = {'id': 'testcate', 'name': 'testcate'}

        resp = self.client.post(self.api_url_base + '/category/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_category(payload_json['id'])
        self.assertResponseRestfulAndSuccess(resp)

        category = self.get_json(resp)['category']
        self.assertEqual(payload_json['name'], category['name'])

    def test_create_cate_using_illegal_id(self):
        payload_json = {'id': 'testcate.illegal', 'name': 'testcate'}

        resp = self.client.post(self.api_url_base + '/category/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_create_cate_using_illegal_name(self):
        payload_json = {'id': 'testcate', 'name': ''}

        resp = self.client.post(self.api_url_base + '/category/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'name')

    def test_create_cate_using_duplicated_id(self):
        payload_json = {'id': 'testcate', 'name': 'testcate'}

        self.client.post(self.api_url_base + '/category/',
                         content_type='application/json',
                         data=json_dumps(payload_json))

        payload_json['name'] += '_'
        resp = self.client.post(self.api_url_base + '/category/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertIn('id', self.get_json(resp)['errors'])

    def test_create_cate_using_duplicated_name(self):
        payload_json = {'id': 'testcate', 'name': 'testcate'}

        self.client.post(self.api_url_base + '/category/',
                         content_type='application/json',
                         data=json_dumps(payload_json))

        payload_json['id'] += '-'
        resp = self.client.post(self.api_url_base + '/category/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertIn('name', self.get_json(resp)['errors'])

    def test_modify_cate(self):
        self.logout()
        self.login_as_su()
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        payload_json = {'name': 'testcate new'}
        resp = self.client.patch(self.api_url_base + '/category/' + cate.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestfulAndSuccess(resp)

        category = self.get_json(resp)['category']
        self.assertEqual(category['name'], payload_json['name'])

    def test_modify_cate_using_illegal_name(self):
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        payload_json = {'name': ''}
        resp = self.client.patch(self.api_url_base + '/category/' + cate.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'name')

    def test_modify_cate_using_nonexist_category_id(self):
        cate_id = 'fake id'
        payload_json = {'name': 'testcate'}

        resp = self.client.patch(self.api_url_base + '/category/' + cate_id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_modify_cate_created_by_other(self):
        self.logout()
        self.login_as_author()
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        self.login_as_su()
        payload_json = {'name': 'testcate new'}
        resp = self.client.patch(self.api_url_base + '/category/' + cate.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestfulAndSuccess(resp)

        category = self.get_json(resp)['category']
        self.assertEqual(category['name'], payload_json['name'])

    def test_modify_cate_created_by_other_without_permission(self):
        self.logout()
        self.login_as_su()
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        self.login_as_author()
        payload_json = {'name': 'testcate new'}
        resp = self.client.patch(self.api_url_base + '/category/' + cate.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'permission')

    def test_delete_cate(self):
        self.login_as_su()
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        resp = self.client.delete(self.api_url_base + '/category/' + cate.id)
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_category(cate.id)
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_delete_cate_using_nonexist_category_id(self):
        cate_id = 'hello'

        resp = self.client.delete(self.api_url_base + '/category/' + cate_id)
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_delete_non_empty_cate(self):
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')
            Article.create(id='testart', title='testart',
                           text_type='md', source_text='# hello',
                           category=cate)

        resp = self.client.delete(self.api_url_base + '/category/' + cate.id)
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'not_empty')

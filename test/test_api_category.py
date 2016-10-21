from json import dumps as json_dumps

from core.models import Category
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

    def test_delete_cate_created_by_other_author(self):
        self.logout()
        self.login_as_author()
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        self.login_as_su()
        resp = self.client.delete(self.api_url_base + '/category/' + cate.id)
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_category(cate.id)
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_delete_cate_created_by_other_author_without_permission(self):
        self.logout()
        self.login_as_su()
        with self.app.test_request_context():
            cate = Category.create(id='testcate', name='testcate')

        self.login_as_author()
        resp = self.client.delete(self.api_url_base + '/category/' + cate.id)
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'permission')

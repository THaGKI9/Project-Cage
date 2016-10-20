from json import dumps as json_dumps

from core.models import User
from test import BaseTestCase


class ApiUserTestCase(BaseTestCase):
    def setUp(self):
        self.reset_database()
        self.logout()

    def get_user(self, id):
        return self.client.get(self.api_url_base + '/user/' + id)

    def test_create_user(self):
        payload_json = {
            'id': 'testid',
            'password': 'longenough',
            'name': 'testname'
        }
        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))

        self.assertResponseRestfulAndSuccess(resp)
        self.assertEqual(self.get_json(resp)['user']['id'], payload_json['id'])

        resp = self.get_user(payload_json['id'])
        self.assertResponseRestfulAndSuccess(resp)

        user = self.get_json(resp)['user']
        self.assertEqual(payload_json['id'], user['id'])
        self.assertEqual(payload_json['name'], user['name'])

    def test_create_expired_user(self):
        payload_json = {
            'id': 'testid',
            'password': 'longenough',
            'name': 'testname',
            'expired': True
        }
        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseRestful(resp)

        resp = self.get_user(payload_json['id'])
        self.assertResponseRestfulAndSuccess(resp)
        self.assertEqual(payload_json['expired'],
                         self.get_json(resp)['user']['expired'])

    def test_create_user_using_illegal_user_id(self):
        payload_json = {
            'id': 'too long to match the pattern',
            'password': 'longenough',
            'name': 'testname',
        }
        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))

        self.assertResponseErrorInField(resp, 'id')

    def test_create_user_using_illegal_password(self):
        payload_json = {
            'id': 'testid',
            'password': 'short',
            'name': 'testname',
        }

        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseErrorInField(resp, 'password')

    def test_create_user_using_illegal_name(self):
        payload_json = {
            'id': 'testid',
            'password': 'longenough',
            'name': 'too long to match the pattern',
        }

        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))
        self.assertResponseErrorInField(resp, 'name')

    def test_create_user_using_duplicated_user_id(self):
        payload_json = {
            'id': 'testid',
            'password': 'longenough',
            'name': 'testname',
        }
        self.client.post(self.api_url_base + '/user/',
                         content_type='application/json',
                         data=json_dumps(payload_json))

        payload_json['name'] = 'testname_'
        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))

        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_create_user_using_duplicated_user_name(self):
        payload_json = {
            'id': 'testid',
            'password': 'longenough',
            'name': 'testname',
        }
        self.client.post(self.api_url_base + '/user/',
                         content_type='application/json',
                         data=json_dumps(payload_json))

        payload_json['id'] = 'testid_'
        resp = self.client.post(self.api_url_base + '/user/',
                                content_type='application/json',
                                data=json_dumps(payload_json))

        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'name')

    def test_get_users(self):
        limit = 40
        with self.db.atomic():
            users = [dict(id='testid' + str(i), password='00000000',
                          name='testname' + str(i))
                     for i in range(100)]
            User.insert_many(users).execute()

        resp = self.client.get(self.api_url_base + '/users/',
                               query_string={'limit': limit})
        self.assertResponseRestful(resp)

        json = self.get_json(resp)
        self.assertEqual(len(json['users']), limit)
        self.assertIn('id', json['users'][0])
        self.assertIn('name', json['users'][0])

    def test_modify_user(self):
        with self.ctx:
            user = User.create(id='testid', password='longenough',
                               name='testname')

        payload_json = {
            'name': 'testname_',
            'password': 'longenough',
            'expired': True
        }
        self.login_as_su()
        resp = self.client.patch(self.api_url_base + '/user/' + user.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestfulAndSuccess(resp)

        user = User.get(User.id == user.id)
        password_cipher = self.encode_password(payload_json['password'])
        self.assertEqual(user.password, password_cipher)
        self.assertEqual(user.name, payload_json['name'])
        self.assertEqual(user.expired, payload_json['expired'])

    def test_modify_user_using_illegal_name(self):
        with self.ctx:
            user = User.create(id='testid', password='longenough',
                               name='testname')

        self.login_as_su()
        payload_json = dict(name='too long to match the pattern')
        resp = self.client.patch(self.api_url_base + '/user/' + user.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))

        self.assertResponseErrorInField(resp, 'name')

    def test_modify_user_using_illegal_password(self):
        with self.ctx:
            user = User.create(id='testid', password='longenough',
                               name='testname')

        self.login_as_su()
        payload_json = dict(password='too long to match the pattern')
        resp = self.client.patch(self.api_url_base + '/user/' + user.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseErrorInField(resp, 'password')

    def test_modify_user_with_nothing_changed(self):
        with self.ctx:
            user = User.create(id='testid', password='longenough',
                               name='testname')

        self.login_as_su()
        resp = self.client.patch(self.api_url_base + '/user/' + user.id,
                                 content_type='application/json',
                                 data=json_dumps({}))
        self.assertResponseRestfulAndSuccess(resp)

    def test_modify_user_to_duplicated_name(self):
        with self.ctx:
            User.create(id='testid', password='longenough', name='testname')
            user = User.create(id='testid_', password='longenough',
                               name='testname_')

        self.login_as_su()
        payload_json = dict(name='testname')
        resp = self.client.patch(self.api_url_base + '/user/' + user.id,
                                 content_type='application/json',
                                 data=json_dumps(payload_json))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'name')

    def test_modify_nonexist_user(self):
        fake_id = 'mustnotexist'

        self.login_as_su()
        resp = self.client.patch(self.api_url_base + '/user/' + fake_id,
                                 content_type='application/json',
                                 data=json_dumps({}))
        self.assertResponseRestful(resp)
        self.assertResponseErrorInField(resp, 'id')

    def test_modify_other_user_using_no_permission(self):
        self.logout()
        self.login_as_author()
        resp = self.client.patch(self.api_url_base + '/user/' + 'su',
                                 content_type='application/json',
                                 data=json_dumps(dict(name='hello')))
        self.assertResponseErrorInField(resp, 'permission')

    def test_delete_user(self):
        with self.ctx:
            user = User.create(id='testid', password='longenough',
                               name='testname')

        resp = self.client.delete(self.api_url_base + '/user/' + user.id)
        self.assertResponseRestfulAndSuccess(resp)

        resp = self.get_user(user.id)
        self.assertResponseErrorInField(resp, 'id')

    def test_delete_nonexist_user(self):
        fake_id = 'whoami'
        resp = self.client.delete(self.api_url_base + '/user/' + fake_id)
        self.assertResponseErrorInField(resp, 'id')

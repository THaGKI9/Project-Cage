from flask_login import current_user

from test import BaseTestCase

from core.models import User


class ApiAuthTestCase(BaseTestCase):
    def setUp(self):
        self.reset_database()

    def login(self, username, password, timestamp=None, remember=False):
        timestamp = timestamp or self.get_timestamp()
        cipher = self.encode_password(password, timestamp)
        # print(self.encode_password(password))
        params = {
            'id': username,
            'password': cipher,
            'timestamp': timestamp,
            'remember': str(remember).lower()
        }
        # print(params)
        return self.client.get(self.api_url_base + '/login/',
                               query_string=params)

    def test_login(self):
        with self.ctx:
            password = '00000000'
            user = User.create(id='su_', password=password, name='testuser')

        with self.client:
            resp = self.login(user.id, password)
            self.assertResponseRestfulAndSuccess(resp)
            self.assertEqual(current_user.name, user.name)

    def test_login_remember(self):
        with self.ctx:
            password = '00000000'
            user = User.create(id='su_', password=password, name='testuser')

        with self.client:
            resp = self.login(user.id, password, remember=True)
            self.assertResponseRestfulAndSuccess(resp)
            self.assertEqual(current_user.name, user.name)

            cookies = {cookie.name: cookie.value
                       for cookie in self.client.cookie_jar}
            remember_token = cookies.get('remember_token', '')
            self.assertNotEqual(remember_token, '')

    def test_login_using_wrong_password(self):
        with self.ctx:
            password = '00000000'
            user = User.create(id='su_', password=password, name='testuser')

        with self.client:
            resp = self.login(user.id, password + 'fake')
            self.assertResponseErrorInField(resp, 'password')

    def test_login_using_nonexist_user_id(self):
        with self.client:
            resp = self.login('whoami', '00000000aaaaaaaaaa')
            self.assertResponseErrorInField(resp, 'id')

    def test_login_timeout(self):
        with self.ctx:
            password = '00000000'
            user = User.create(id='su_', password=password, name='testuser')

        with self.client:
            fake_timestamp = self.get_timestamp() - self.login_timeout - 100000
            resp = self.login(user.id, password, fake_timestamp)
            self.assertResponseErrorInField(resp, 'timestamp')

    def test_logout(self):
        with self.ctx:
            password = '00000000'
            user = User.create(id='su_', password=password, name='testuser')

        with self.client:
            resp = self.login(user.id, password)
            self.assertResponseRestfulAndSuccess(resp)

            self.client.get(self.api_url_base + '/logout/')
            self.assertFalse(current_user.is_authenticated)

            # logout without authentication
            self.client.get(self.api_url_base + '/logout/')
            self.assertFalse(current_user.is_authenticated)

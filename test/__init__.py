import logging
from unittest import TestCase

from config import TestingConfig
from core import create_app, db


logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())


class BaseTestCase(TestCase):
    app = create_app(TestingConfig)
    client = app.test_client()
    db = db.database
    ctx = app.app_context()
    api_url_base = TestingConfig.API_URL_BASE
    password_salt = TestingConfig.USER_PASSWORD_SALT
    login_timeout = TestingConfig.USER_LOGIN_TIMEOUT

    def reset_database(self):
        from core.models import User, tables
        from core.models.permission import (preset_for_author,
                                            preset_for_superuser)

        with self.ctx:
            db.database.drop_tables(tables, safe=True)
            db.database.create_tables(tables)

            User.create(id='su', permission=preset_for_superuser,
                        password='00000000', name='超级管理员')
            User.create(id='author', permission=preset_for_author,
                        password='00000000', name='作者')

    def get_timestamp(self):
        from time import time
        return int(time() * 1000)

    def encode_password(self, plain_password, timestamp=None):
        from hashlib import sha1
        raw = (plain_password + self.password_salt).encode('utf-8')
        cipher = sha1(raw).hexdigest()
        if timestamp is not None:
            cipher = sha1((cipher + str(timestamp)).encode()).hexdigest()
        return cipher

    def login(self, user_id):
        from flask_login import encode_cookie

        with self.client.session_transaction():
            self.client.set_cookie(
                self.app.config['SERVER_NAME'],
                'remember_token',
                encode_cookie(user_id)
            )

    def logout(self):
        with self.client.session_transaction() as session:
            self.client.delete_cookie(self.app.config['SERVER_NAME'],
                                      'remember_token')
            session.pop('user_id', None)
            session.pop('_fresh', None)

    def login_as_su(self):
        return self.login('su')

    def login_as_author(self):
        return self.login('author')

    def get_json(self, resp):
        from json import loads
        return loads(resp.data.decode())

    def toggle_sql_echo(self):
        if logger.level == 0:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARNING)

    def assertResponseOk(self, resp):
        self.assertEqual(resp.status_code, 200)

    def assertResponseRestful(self, resp):
        self.assertResponseOk(resp)
        self.assertEqual(resp.content_type, 'application/json')

    def assertResponseRestfulAndSuccess(self, resp):
        self.assertResponseRestful(resp)
        self.assertIsNone(self.get_json(resp)['$errors'])

    def assertJSONHasKey(self, resp_or_dict, key):
        if isinstance(resp_or_dict, dict):
            json = resp_or_dict
        else:
            json = self.get_json(resp_or_dict)
        self.assertIn(key, json)

    def assertResponseErrorInField(self, resp, error_field):
        self.assertResponseRestful(resp)
        json = self.get_json(resp)['$errors']
        self.assertIsInstance(json, dict)
        self.assertIn(error_field, json)

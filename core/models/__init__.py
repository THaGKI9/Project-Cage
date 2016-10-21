from collections import OrderedDict
from datetime import datetime
from hashlib import sha1

from flask import request
from flask_login import AnonymousUserMixin, UserMixin, current_user
from peewee import (BigIntegerField, BooleanField, DateTimeField,
                    ForeignKeyField, IntegerField, TextField)

from core import app_config, db
from core.helpers import make_raw_request_line

from .permission import Permission


db.Model._meta.only_save_dirty = True


def _get_user():
    return current_user.get_id()


# Database Model
class User(db.Model, UserMixin):
    id = TextField(primary_key=True)
    name = TextField(unique=True, null=False)
    password = TextField(null=False)
    permission = BigIntegerField(default=0)
    expired = BooleanField(default=False)
    last_login = DateTimeField(default=datetime.utcfromtimestamp(0))
    create_time = DateTimeField(default=datetime.utcnow)

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        if kargs.get('password') is not None:
            self.set_password(kargs.pop('password'))

    def to_dict(self, with_perimission=False):
        rv = OrderedDict()
        rv['id'] = self.id
        rv['name'] = self.name
        if with_perimission:
            rv['permission'] = Permission.format_permission(self.permission)
        rv['expired'] = self.expired
        rv['last_login'] = self.last_login
        return rv

    def can(self, permission):
        return bool(self.permission & permission)

    def check_password(self, enc_password, timestamp):
        cipher = sha1((self.password + str(timestamp)).encode()).hexdigest()
        return cipher == enc_password

    def set_password(self, plain_password):
        salt = app_config['USER_PASSWORD_SALT']
        raw = (plain_password + salt).encode('utf-8')
        self.password = sha1(raw).hexdigest()

    @property
    def is_active(self):
        return not self.expired


class Category(db.Model):
    id = TextField(primary_key=True)
    name = TextField(unique=True)
    create_time = DateTimeField(default=datetime.utcnow)
    create_by = ForeignKeyField(User, default=_get_user, null=True,
                                on_update='CASCADE', on_delete='SET NULL')

    def annotate(self):
        return self.select().annotate(Article)

    def to_dict(self):
        rv_dict = OrderedDict()
        rv_dict['id'] = self.id
        rv_dict['name'] = self.name

        if hasattr(self, 'count'):
            rv_dict['article_count'] = self.count
        return rv_dict


class Article(db.Model):
    id = TextField(primary_key=True)

    is_commentable = BooleanField(default=True)
    title = TextField()
    text_type = TextField()
    source_text = TextField()
    content = TextField(null=True)
    read_count = IntegerField(default=0)
    post_time = DateTimeField(default=datetime.utcnow)
    update_time = DateTimeField(default=datetime.utcnow)
    public = BooleanField(default=True)

    category = ForeignKeyField(Category, null=True,
                               on_update='CASCADE', on_delete='SET NULL',
                               related_name='articles')
    author = ForeignKeyField(User, default=_get_user, null=True,
                             on_delete='SET NULL', on_update='CASCADE',
                             related_name='articles')

    @property
    def comment_count(self):
        return Comment.select().filter(Comment.article == self.id).count()

    def to_dict(self, with_content=False, with_src=False):
        rv_dict = OrderedDict()
        rv_dict['id'] = self.id
        rv_dict['title'] = self.title
        rv_dict['author'] = OrderedDict()
        if self.author:
            rv_dict['author']['id'] = self.author.id
            rv_dict['author']['name'] = self.author.name
        rv_dict['category'] = OrderedDict()
        if self.category:
            rv_dict['category']['id'] = self.category.id
            rv_dict['category']['name'] = self.category.name
        if with_content:
            rv_dict['content'] = self.content
        rv_dict['is_commentable'] = self.is_commentable
        rv_dict['read_count'] = self.read_count
        rv_dict['post_time'] = self.post_time
        rv_dict['update_time'] = self.update_time
        if with_src:
            rv_dict['text_type'] = self.text_type
            rv_dict['source_text'] = self.source_text
        return rv_dict


class Comment(db.Model):
    content = TextField()
    nickname = TextField(null=True)
    reviewed = BooleanField(default=False)
    create_time = DateTimeField(default=datetime.utcnow)
    ip_address = TextField(default=lambda: request.remote_addr, null=True)
    is_anonymous = BooleanField(default=False)

    user = ForeignKeyField(User, default=_get_user, null=True,
                           on_update='CASCADE', on_delete='CASCADE')
    article = ForeignKeyField(Article,
                              on_update='CASCADE', on_delete='CASCADE')
    parent = ForeignKeyField('self', null=True,
                             on_delete='CASCADE', on_update='CASCADE',
                             related_name='sub_comments')

    @property
    def display_name(self):
        return '[Author]' + self.user.name if self.is_author else self.nickname

    def to_dict(self):
        rv_dict = OrderedDict()
        rv_dict['comment_id'] = self.id
        rv_dict['content'] = self.content
        rv_dict['author'] = self.display_name
        rv_dict['time'] = self.time
        rv_dict['replies'] = [comments.to_dict()
                              for comments in self.sub_comments]
        return rv_dict


class Event(db.Model):
    type = TextField()
    description = TextField()
    ip_address = TextField(default=lambda: request.remote_addr, null=True)
    endpoint = TextField(default=lambda: request.endpoint)
    request = TextField(default=make_raw_request_line)
    create_time = DateTimeField(default=datetime.utcnow)

    user = ForeignKeyField(User, default=_get_user, null=True,
                           on_update='CASCADE', on_delete='CASCADE')


# For :ref:`flask_login`
class AnonymousUser(AnonymousUserMixin):
    permission = None

    def can(self, permission):
        pass


User._meta.db_table = 'users'
tables = [User, Category, Article, Comment, Event]

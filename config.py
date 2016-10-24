from peewee import SqliteDatabase


class Config:
    SECRET_KEY = '^gR_rQp`#;v!:OLfy4!E2vTN`q~w($v!CRR'

    ENABLE_PERMISSION_CONTROL = True
    API_URL_BASE = '/api'

    HOMEPAGE_ENDPOINT = 'view.index'

    DISPLAY_TIMEZONE = 'UTC+8'
    DISPLAY_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    USER_LOGIN_TIMEOUT = 30 * 3600 * 1000
    USER_LIST_DEFAULT_LIMIT = 20

    USER_USERID_PATTERN = r'^[0-9a-zA-z_]{5,32}$'
    USER_USERID_DESCRIPTION = '有效值：长度5-32，只含大小写字母、数字、下划线'
    USER_PASSWORD_SALT = r'r9q.v9v[b7xnw4]4tzeiz.vlpu,iq/l5'
    USER_PASSWORD_PATTERN = r'^[^\s]{10,32}$'
    USER_PASSWORD_DESCRIPTION = '有效值：长度10-32'
    USER_NAME_PATTERN = r'^[^\t\r\n]{1,12}$'
    USER_NAME_DESCRIPTION = '有效值：长度1-12'

    CATEGORY_ID_PATTERN = r'^[-0-9a-z]{1,}$'
    CATEGORY_ID_DESCRIPTION = '有效值：长度至少为1，只含小写字母、数字或横杠'

    ARTICLE_LIST_DEFAULT_LIMIT = 20
    ARTICLE_ID_PATTERN = CATEGORY_ID_PATTERN
    ARTICLE_ID_DESCRIPTION = CATEGORY_ID_DESCRIPTION

    COMMENT_NEED_REVIEW = True
    COMMENT_LIST_DEFAULT_LIMIT = 20

    @classmethod
    def init_app(cls, app):
        pass


class ProductionConfig(Config):
    pass


class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE = SqliteDatabase('./databases/cage_dev.db', pragmas=(
        ('foreign_keys', 'ON'),
    ))

    @classmethod
    def init_app(cls, app):
        from os.path import exists
        from os import mkdir

        if not exists('./databases'):
            mkdir('./databases')


class TestingConfig(Config):
    TESTING = True
    SERVER_NAME = 'TestServer.local'

    DATABASE = SqliteDatabase('./databases/cage_test.db', pragmas=(
        ('foreign_keys', 'ON'),
    ))

    # disable permission control
    # because general unittest doesn't involve any permission control.
    ENABLE_PERMISSION_CONTROL = False

    @classmethod
    def init_app(cls, app):
        from os.path import exists
        from os import mkdir

        if not exists('./databases'):
            mkdir('./databases')

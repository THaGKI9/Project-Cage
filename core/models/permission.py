from collections import OrderedDict
from enum import Enum

__all__ = ['Permission', 'preset_for_superuser', 'preset_for_author']


class Group:
    flags = []
    name = None

    def __init__(self, name, flags):
        self.name = name
        self.flags = flags


class Flag:
    value = None
    description = None

    def __init__(self, bit, description):
        self.value = 1 << bit
        self.description = description


class Permission(Enum):
    __groups__ = OrderedDict()

    CONFIGURE_SYSTEM = Flag(1, '')

    READ_USER = Flag(4, '')
    CREATE_USER = Flag(5, '')
    MODIFY_USER = Flag(6, '')
    MODIFY_OTHER_USER = Flag(7, '')
    DELETE_USER = Flag(8, '')

    READ_ARTICLE = Flag(8 + 1, '')
    POST_ARTICLE = Flag(8 + 2, '')
    EDIT_ARTICLE = Flag(8 + 3, '')
    EDIT_OTHERS_ARTICLE = Flag(8 + 4, '')

    READ_CATEGORY = Flag(8 + 5, '')
    CREATE_CATEGORY = Flag(8 + 6, '')
    EDIT_CATEGORY = Flag(8 + 7, '')
    EDIT_OTHERS_CATEGORY = Flag(8 + 8, '')

    READ_COMMENT = Flag(16 + 1, '')
    WRITE_COMMENT = Flag(16 + 2, '')
    REVIEW_COMMENT = Flag(16 + 3, '')
    REIVEW_OTHERS_COMMENT = Flag(16 + 4, '')

    @classmethod
    def add_group(cls, name, flags):
        """Group flags.

        :param name: group name
        :param iterable flags: a iterable object contains :class:`FLag`
        """
        flags_list = []
        for flag in flags:
            flag_dict = OrderedDict()
            flag_dict['name'] = flag._name_
            flag_dict['description'] = flag.value.description
            flags_list.append(flag_dict)
        cls.__groups__[name] = flags_list

    @classmethod
    def get_groups(cls):
        return cls.__groups__

    @classmethod
    def format_permission(cls, permission_value):
        """Convert numberic permission value to a list of
        permission flags.

        :param int permission_value:
        :return: a list contains permission flags.
        :rtype: list
        """
        return [
            permission.name
            for permission in cls
            if permission_value & permission.value
        ]

    @classmethod
    def parse_permission(cls, permission_list):
        """Convert permission flags to a numberic permission value.
        The undefined permission will be ignored.

        :param iterable permission_list: an iterable object, contains
            permission flags defined in :class:``Permission``
        :return: permission value
        :rtype: int
        """
        permission_value = 0
        for permission in permission_list:
            try:
                permission_value |= cls[permission].value
            except KeyError:
                pass
        return permission_value

    def __or__(self, flag_int):
        if isinstance(flag_int, Permission):
            return self.value.value | flag_int.value.value
        return self.value.value | flag_int

    def __xor__(self, flag_int):
        if isinstance(flag_int, Permission):
            return self.value.value ^ flag_int.value.value
        return self.value.value ^ flag_int

    def __and__(self, flag_int):
        if isinstance(flag_int, Permission):
            return self.value.value & flag_int.value.value
        return self.value.value & flag_int

    def __ror__(self, other):
        return other | self.value.value

    def __rxor__(self, other):
        return other ^ self.value.value

    def __rand__(self, other):
        return other & self.value.value

Permission.add_group(
    name='System Configuration',
    flags=[Permission.CONFIGURE_SYSTEM]
)

Permission.add_group(
    name='User Operation',
    flags=[
        Permission.READ_USER,
        Permission.CREATE_USER,
        Permission.MODIFY_USER,
        Permission.MODIFY_OTHER_USER,
        Permission.DELETE_USER
    ]
)

Permission.add_group(
    name='Article Operation',
    flags=[
        Permission.READ_ARTICLE,
        Permission.POST_ARTICLE,
        Permission.EDIT_ARTICLE,
        Permission.EDIT_OTHERS_ARTICLE
    ]
)

Permission.add_group(
    name='Category Operation',
    flags=[
        Permission.READ_CATEGORY,
        Permission.CREATE_CATEGORY,
        Permission.EDIT_CATEGORY,
        Permission.EDIT_OTHERS_CATEGORY
    ]
)

Permission.add_group(
    name='Comment Operation',
    flags=[
        Permission.READ_COMMENT,
        Permission.WRITE_COMMENT,
        Permission.REVIEW_COMMENT,
        Permission.REIVEW_OTHERS_COMMENT
    ]
)

"""Preset permission for Superuser: All"""
preset_for_superuser = int('1' * 63, 2)

"""Preset permission for Author:

    * READ_ARTICLE
    * POST_ARTICLE
    * EDIT_ARTICLE
    * READ_CATEGORY
    * POST_CATEGORY
    * EDIT_CATEGORY
    * READ_COMMENT
    * READ_ALL_COMMENT
    * WRITE_COMMENT
    * REVIEW_COMMENT
"""
preset_for_author = Permission.parse_permission([
    Permission.READ_ARTICLE,
    Permission.POST_ARTICLE,
    Permission.EDIT_ARTICLE,
    Permission.READ_CATEGORY,
    Permission.CREATE_CATEGORY,
    Permission.EDIT_CATEGORY,
    Permission.READ_COMMENT,
    Permission.WRITE_COMMENT,
    Permission.REVIEW_COMMENT
])

if __name__ == '__main__':
    from json import dumps
    print(dumps(Permission.get_groups(), indent=2))

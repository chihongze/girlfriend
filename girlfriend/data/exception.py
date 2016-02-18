# coding: utf-8

"""数据结构定义所需要用到的异常类
"""

from girlfriend.exception import GirlFriendSysException


class IndexOutOfBoundsException(GirlFriendSysException):
    """索引越界时抛出此异常
    """
    pass


class MissingKeyException(GirlFriendSysException):
    """在key-value的结构中，当key所引用的数据不存在时抛出此异常
    """
    pass


class InvalidSizeException(GirlFriendSysException):
    """当目标集合的尺寸不符合要求时抛出此异常
    """
    pass

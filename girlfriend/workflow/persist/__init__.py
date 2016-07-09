# coding: utf-8

"""该模块包含关于工作流持久化操作的抽象
"""

from abc import (
    ABCMeta,
    abstractmethod,
)
from girlfriend.exception import GirlFriendSysException


class RecoverInfo(object):

    """
    从持久化中加载的用于恢复工作流执行的信息
    """

    def __init__(self, begin_unit, context_factory):
        """
        :param begin_unit 起始单元
        :param context_factory 上下文工厂
        """
        self._begin_unit = begin_unit
        self._context_factory = context_factory

    @property
    def begin_unit(self):
        return self._begin_unit

    @property
    def context_factory(self):
        return self._context_factory


class NoNeedRecoverException(GirlFriendSysException):

    """
    当工作流无需恢复时抛出该异常，比如持久化数据不存在，或者对应的工作流已经成功完成等等。
    该异常需要由工作流的驱动程序来捕获。
    """
    pass


class RecoverPolicy(object):

    """
    RecoverPolicy用于为工作流的调用者提供恢复策略
    恢复策略包含两方面的内容，一个是当前工作流要执行的起始点，
    另外就是关于Context的恢复策略，需要提供一个可以恢复旧有数据的上下文工场
    """

    __meta__ = ABCMeta

    @abstractmethod
    def load(self):
        """用于恢复持久化的上下文信息，由工作流的驱动程序回调。
           当工作流不需要恢复时，会抛出NoNeedRecoverException
        """
        pass

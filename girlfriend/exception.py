# coding: utf-8

"""所有Girlfriend内部公共异常都定义在这里
"""

import types
import locale


class GirlFriendException(Exception):

    """GirlFriend系统中所有的异常都要继承此异常类
    """

    def __init__(self, msg):
        """
            :param msg 可以是一个字符串，也可以是一个key为locale的字典
        """
        if isinstance(msg, types.DictType):
            country_code, _ = locale.getlocale(locale.LC_ALL)
            msg = msg[country_code]

        if isinstance(msg, unicode):
            super(GirlFriendException, self).__init__(msg.encode("utf-8"))
            self.msg = msg
        elif isinstance(msg, str):
            super(GirlFriendException, self).__init__(msg)
            self.msg = msg.decode("utf-8")
        else:
            raise TypeError

    def __unicode__(self):
        return self.msg


class GirlFriendBizException(GirlFriendException):

    """业务相关的异常，属于意料之中的用户错误，捕获该异常之后可以按照正常的业务流程进行处理，
       常用于面向最终用户的Facade层。最常见的场景就是在命令行工具中，可以捕获该异常，
       向用户输出错误消息并退出或者重新输入参数，因为是正常的逻辑错误，无需上报Bug和输出错误日志。
    """
    pass


class GirlFriendSysException(GirlFriendException):

    """系统相关的异常，多用于框架内部以及向插件开发者提供的工具和数据结构，
       该异常跟业务无关，属于系统错误，无法继续进行业务处理，
       只能输出错误日志、打印错误堆栈进行调试或者将错误上报给开发者。
    """
    pass


class InvalidArgumentException(GirlFriendSysException):

    """当函数输入的参数不正确时抛出此异常
    """
    pass


class InvalidTypeException(GirlFriendSysException):

    """当接受的参数对象类型不符合预期时抛出此异常
    """
    pass


class UnknownWitchToExecuteException(GirlFriendSysException):

    """多数用于委托的场景，如果委托的对象有多种表现形式，指定的表现形式冲突，
       就会抛出此异常，比如一个Job既可以接受插件，又可以接受普通的回调函数，如果
       两个都指定了，那么就会不知道到底该执行哪个
    """
    pass


class UnsupportMethodException(GirlFriendSysException):

    """当实现一个抽象类时，如果某些方法无法满足约定实现，那么可以抛出该异常，
       外部调用该对象的框架必须知道并处理这种异常情况。
    """
    pass


class InvalidStatusException(GirlFriendSysException):

    """当状态不满足时，抛出此异常
    """
    pass

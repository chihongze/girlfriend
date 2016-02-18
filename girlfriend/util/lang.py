# coding: utf-8

"""封装常用的设计模式以及对内置函数和方法进行约定性的简化
"""

import types
import inspect
from functools import wraps
from girlfriend.exception import GirlFriendSysException

_singletons = {}


def singleton(clazz):
    """单例修饰器，被修饰的类在系统中都是单例的
       非线程安全，请勿用在多线程环境当中
    """

    @wraps(clazz)
    def constructor(*args, **kws):
        global _singletons
        instance = _singletons.get(clazz)
        if instance is None:
            instance = clazz(*args, **kws)
            _singletons[clazz] = instance
        return instance

    return constructor


class DelegateMeta(type):

    """该元类用于实现委托
       基本用法:

       class A(object):

            __metaclass__ = DelegateMeta

            def __init__(self, delegate):
                self.delegate = delegate

        lst = [1,2,3]
        a = A(lst)
        a.append(4)

        对象a的append方法会自动委托到lst对象的append方法。
        这样可以满足多数情况，但是碰到内置方法比如__getitem__无法自动实现委托
        如果要委托内置方法，那么需要通过类属性delegate_internal_methods去指明

        class B(object):
            __metaclass__ = DelegateMeta
            delegate_internal_methods = (
                "__getitem__",
                "__hash__",
                "__eq__"
            )

            def __init__(self, delegate):
                self.delegate = delegate

        需要值得注意的是，不要委托特殊方法：__init__、__new__
        另外还有__getattr__以及__getattribute__也不可以委托，因为DelegateMeta会用到这两个方法
        如果需要在委托类中对访问属性做控制，那么可以使用__myattr__(self, fieldname)
        对于未定义属性，DelegateMeta会优先拦截__myattr__，__myattr__通过抛出UnknownAttrError通知
        委托类进行接下来的处理。

        还可以使用delegate_methods属性显式指定委托方法:

        class C(object):
            __metaclass__ = DelegateMeta
            delegate_methods = (
                "append",
                "__getitem__",
                "__eq__"
            )

            def __init__(self, delegate):
                self.delegate = delegate

    """

    class UnknownAttrError(GirlFriendSysException):
        pass

    def __new__(cls, name, bases, attrs):
        delegate_methods = attrs.get("delegate_methods", tuple())
        if delegate_methods:
            DelegateMeta.register_delegates(delegate_methods, attrs)
            return type(name, bases, attrs)

        def getter(self, method_name):
            if "__myattr__" in attrs:
                try:
                    return self.__myattr__(method_name)
                except DelegateMeta.UnknownAttrError:
                    pass

            def method(*args, **kws):
                mtd = getattr(self.delegate, method_name)
                if mtd:
                    return mtd(*args, **kws)
                else:
                    raise AttributeError(
                        "No method found %s" % method_name)
            return method

        attrs["__getattr__"] = getter

        # 痛!
        delegate_internal_methods = attrs.get(
            "delegate_internal_methods", tuple())
        DelegateMeta.register_delegates(delegate_internal_methods, attrs)
        return type(name, bases, attrs)

    @staticmethod
    def register_delegates(delegate_methods, attrs):
        for mtd_name in delegate_methods:
            def make_method(method_name):
                def method(self, *args, **kws):
                    return getattr(self.delegate,
                                   method_name)(*args, **kws)
                return method
            attrs[mtd_name] = make_method(mtd_name)


def args2fields(private=True):
    """专门是应用于构造函数的修饰器
       可以将构造函数除self以外的参数悉数赋值给类属性

       比如

       class A(object):

            def __init__(self, a, b, c):
                self._a = a
                self._b = b
                self._c = c
                self.sum = self._a + self._b + self._c

        只要写成这样就好:

        class A(object):

            @args2fields()
            def __init__(self, a, b, c):
                self.sum = self._a + self._b + self._c

        不必再去写上面那些无聊的赋值语句了

        :param private 是否转变为私有字段，如果为True，那么会在所有字段名前加个下划线
    """

    def _field_name(arg_name):
        return "_" + arg_name if private else arg_name

    def _args2fields(constructor):

        @wraps(constructor)
        def _wrapped_constuctor(self, *args, **kws):
            args_spec = inspect.getargspec(constructor)
            for idx, arg in enumerate(args, start=1):
                arg_name = args_spec.args[idx]
                field_name = _field_name(arg_name)
                setattr(self, field_name, arg)
            for arg_name, arg in kws.items():
                field_name = _field_name(arg_name)
                setattr(self, field_name, arg)

            # 处理没有赋值的默认参数
            default_args = get_default_args(args_spec)
            if default_args:
                for arg_name, default_value in default_args.items():
                    if arg_name == "self":
                        continue
                    field_name = _field_name(arg_name)
                    if hasattr(self, field_name):
                        continue
                    setattr(self, field_name, default_value)

            constructor(self, *args, **kws)

        return _wrapped_constuctor

    return _args2fields


def get_default_args(o):
    """获取函数的默认参数名-值映射
    """
    argspec = o
    if not isinstance(o, inspect.ArgSpec):
        argspec = inspect.getargspec(o)
    if not argspec.defaults:
        return {}
    return dict(zip(argspec.args[-len(argspec.defaults):],
                    argspec.defaults))

# 线性集合类型
SequenceCollectionType = (types.ListType, types.TupleType)


def parse_context_var(context, variable_name):
    """解析上下文中的变量
       如果以'$'字符开头，那么返回上下文中的对应变量
       其它的情况会直接返回字符串
       开头两个$$连续为转义，比如'$$aa$$a'为'$aa$$a'
       :param context 上下文
       :param variable_name
    """
    if not isinstance(variable_name, str):
        return variable_name
    elif variable_name.startswith("$$"):
        return variable_name.replace("$$", "$")
    elif variable_name.startswith("$"):
        return context[variable_name[1:]]
    else:
        return variable_name

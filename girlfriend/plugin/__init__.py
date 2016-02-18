# coding: utf-8

"""该模块中描述了插件的基本数据结构和生命周期，
并提供插件编写和管理的基本工具。
"""

import types
import functools
from girlfriend.exception import (
    GirlFriendBizException,
    GirlFriendSysException
)
from girlfriend.util.lang import SequenceCollectionType
from stevedore import extension


class Plugin(object):

    """插件

       GirlFriend中的插件的生命周期

           sys_prepare 在整个系统中只执行一次,用于做一些初始化工作
           execute 用于执行具体的插件逻辑,并通过上下文来进行参数传递
           sys_cleanup 在整个系统中也只执行一次,用于做一些清理工作

       GirlFriend插件的公共属性

           name 插件名称,要确保插件名称的独一无二,可以使用倒置域名法命名
           status 插件状态
           description 插件描述,用于输出帮助信息
    """

    @classmethod
    def wrap_function(cls, name, description,
                      execute, sys_prepare=None, sys_cleanup=None,
                      args_validator=None, config_validator=None):
        """将函数对象包装成插件对象
        :param name: 插件名称
        :param description: 插件描述
        :param execute: 执行函数
        :param sys_prepare: sys_prepare函数,可选
        :param sys_cleanup: sys_cleanup函数,可选
        :param args_validator: 执行参数验证器
        :param config_validator: 配置验证器
        :return: 包装后的Plugin对象
        """
        execute = Plugin.__check_function(
            "execute",
            execute,
            lambda arg_count: arg_count >= 1,
            u"execute函数至少要有一个参数用来接受上下文对象")

        if sys_prepare:
            sys_prepare = Plugin.__check_function(
                "sys_prepare",
                sys_prepare,
                lambda arg_count: arg_count == 1,
                u"sys_prepare函数只能有且只有一个参数来接受配置信息"
            )

        if sys_cleanup:
            sys_cleanup = Plugin.__check_function(
                "sys_cleanup",
                sys_cleanup,
                lambda arg_count: arg_count == 1,
                u"sys_cleanup函数只能有且只有一个参数来接受配置信息"
            )

        return cls(
            name=name,
            description=description,
            execute=execute,
            sys_prepare=sys_prepare,
            sys_cleanup=sys_cleanup,
            args_validator=args_validator,
            config_validator=config_validator
        )

    @staticmethod
    def __check_function(event_name, function, check_arg, msg):
        """检查传入的函数是否符合指定格式
        """
        if not isinstance(function, types.FunctionType):
            raise InvalidPluginException(u"'{}' 参数必须是函数类型".format(event_name))
        if not check_arg(function.func_code.co_argcount):
            raise InvalidPluginException(msg)
        return function

    @classmethod
    def wrap_class(cls, clazz, *args, **kws):
        """将类对象包装为插件对象,例如:

            class TestPlugin(object):

                name = "testing"

                '''
                This is a testing plugin
                '''

                def __init__(self, a, b):
                    self.a = a
                    self.b = b

                def sys_prepare(self, config):
                    print "sys_prepare method"

                def execute(self, context, *args, **kws):
                    print "execute method"

                def sys_cleanup(self, config):
                    print "sys_cleanup method"

            plugin = Plugin.wrap_class(TestPlugin, a=1, b=2)

            Plugin.wrap_class会使用给予的参数来调用插件类的构造函数,
            创建出该类的对象,并把生命周期方法的调用委托给这个新创建的对象,
            name属性默认会取类名,也可以跟上面一样指定一个name类属性,
            description属性会取类的__doc__属性
            其中,execute方法是必须的,sys_prepare和sys_cleanup两个方法是可选的


        :param clazz: 要包装的类对象
        :param args: 构造函数的参数列表
        :param kws: 构造函数的参数列表
        :return: 包装后的Plugin对象
        """

        class_name = clazz.__name__

        if not hasattr(clazz, "execute"):
            raise InvalidPluginException(
                u"类 '{}' 缺失execute方法,无法构建插件".format(class_name))

        # 构建实例
        instance = clazz(*args, **kws)

        # 检查并包装方法
        execute = Plugin.__check_and_wrap_method(
            instance,
            getattr(clazz, "execute", None),
            lambda c: c >= 1,
            u"{}.execute 除了self至少要包含一个参数用来传递context对象".format(class_name)
        )

        sys_prepare = Plugin.__check_and_wrap_method(
            instance,
            getattr(clazz, "sys_prepare", None),
            lambda c: c == 1,
            u"{}.sys_prepare 除了self只能有且只有一个参数来接受config对象".format(class_name)
        )

        sys_cleanup = Plugin.__check_and_wrap_method(
            instance,
            getattr(clazz, "sys_cleanup", None),
            lambda c: c == 1,
            u"{}.sys_cleanup 除了self只能有且只有一个参数来接受config对象".format(class_name)
        )

        # 解决其余属性
        plugin_name = class_name
        if hasattr(clazz, "name"):
            name = getattr(clazz, "name")
            if not name or not name.strip():
                raise InvalidPluginException(
                    u"{}.name 属性不能为空".format(class_name))
            plugin_name = name.strip()

        args_validator = getattr(clazz, "args_validator", tuple())
        config_validator = getattr(clazz, "config_validator", tuple())

        # 集齐了各路神器,召唤神龙!
        return cls(
            name=plugin_name,
            description=clazz.__doc__,
            execute=execute,
            sys_prepare=sys_prepare,
            sys_cleanup=sys_cleanup,
            args_validator=args_validator,
            config_validator=config_validator
        )

    @staticmethod
    def __check_and_wrap_method(instance, mtd, check_arg, msg):
        if not mtd:
            return None
        if not check_arg(mtd.im_func.func_code.co_argcount - 1):
            raise InvalidPluginException(msg)
        return functools.partial(mtd, instance)

    @classmethod
    def wrap_module(cls, module):
        """包装模块对象为Plugin对象,例如test_plugin.py:

            '''测试模块'''

            name = "test_plugin"

            def sys_prepare(config):
                pass

            def execute(config):
                pass

            def sys_cleanup(config):
                pass


        module对象必须包含一个execute函数
        sys_prepare跟sys_cleanup是可选的

        会默认将模块的名称作为插件名称,如果模块中包含了name属性,
        那么name的值将作为插件的名称

        模块的__doc__属性将作为插件的description属性

        :param module: 要包装的模块对象
        :return: 包装后的Plugin对象
        """

        module_name = module.__name__

        if not hasattr(module, "execute"):
            raise InvalidPluginException(
                u"模块 '{}' 必须包含一个execute函数".format(module_name))

        # 检查模块中各个函数是否满足要求

        execute = Plugin.__check_function(
            "execute",
            module.execute,
            lambda c: c >= 1,
            u"模块 '{}' 的execute函数至少要有一个参数用于接收context对象".format(module_name)
        )

        sys_prepare, sys_cleanup = None, None

        if hasattr(module, "sys_prepare"):
            sys_prepare = Plugin.__check_function(
                "sys_prepare",
                module.sys_prepare,
                lambda c: c == 1,
                u"模块 '{}' 的sys_prepare函数必须有一个参数用于接收config对象".format(
                    module_name)
            )

        if hasattr(module, "sys_cleanup"):
            sys_cleanup = Plugin.__check_function(
                "sys_cleanup",
                module.sys_cleanup,
                lambda c: c == 1,
                u"模块 '{}' 的sys_cleanup函数必须有".format(module_name)
            )

        # 获取插件名称
        plugin_name = module_name
        if hasattr(module, "name"):
            name = module.name
            if not name or not name.strip():
                raise InvalidPluginException(
                    u"模块 '{}' 的name属性不能为空".format(name))
            plugin_name = name.strip()

        args_validator = getattr(module, "args_validator", tuple())
        config_validator = getattr(module, "config_validator", tuple())

        return cls(
            name=plugin_name,
            description=module.__doc__,
            execute=execute,
            sys_prepare=sys_prepare,
            sys_cleanup=sys_cleanup,
            args_validator=args_validator,
            config_validator=config_validator
        )

    STATUS_UNPREPARED = 0  # 尚未进行初始化
    STATUS_PREPARED = 1  # 已经进行了初始化,处于可执行状态
    STATUS_DEAD = 2  # 已经进行了清理,无法再使用

    def __init__(self, name, description, execute, sys_prepare, sys_cleanup,
                 args_validator, config_validator):
        """
        :param name: 插件名称,在整个系统中,插件需要有一个独一无二的名称
        :param execute: 插件的执行逻辑,
                        接受一个context参数和其它请求参数的可执行对象
        :param sys_prepare: 初始化钩子,接受一个config参数的可执行对象
        :param sys_cleanup: 清理钩子,接受一个config参数的可执行对象
        :param args_validator: 参数验证器，接受一个rule列表，或者一个自定义的验证函数
        :param config_validator: 配置验证器
        """
        self._name = name
        self._description = description
        self._sys_prepare = sys_prepare
        self._sys_cleanup = sys_cleanup
        self._execute = execute

        # 启用默认的参数验证器
        if args_validator is None or isinstance(
                args_validator, SequenceCollectionType):
            self._args_validator = DefaultArgsValidator(args_validator)
        else:
            self._args_validator = args_validator

        # 启用默认的配置验证器
        if config_validator is None or isinstance(
                config_validator, SequenceCollectionType):
            self._config_validator = DefaultConfigValidator(config_validator)
        else:
            self._config_validator = config_validator

        self._status = Plugin.STATUS_UNPREPARED  # 尚未初始化

    @property
    def name(self):
        return self._name

    @property
    def status(self):
        return self._status

    @property
    def description(self):
        return self._description

    def sys_prepare(self, config):
        """系统初始化
        :param config: 配置信息
        """
        if self.status != Plugin.STATUS_UNPREPARED:
            raise PluginAlreadyPreparedException(
                u"插件 '{}' 已经被初始化了".format(self.name))

        # 执行配置验证
        self._config_validator(config)
        value = None
        if self._sys_prepare:
            value = self._sys_prepare(config)
        self._status = Plugin.STATUS_PREPARED
        return value

    def sys_cleanup(self, config):
        """清理工作,在系统生命周期结束时进行
        :param config: 配置信息
        """
        if self.status == Plugin.STATUS_UNPREPARED:
            raise PluginUnPreparedException(
                u"插件 '{}' 尚未初始化,不能进行清理工作".format(self.name))
        if self.status == Plugin.STATUS_DEAD:
            return
        value = None
        if self._sys_cleanup:
            value = self._sys_cleanup(config)
        self._status = Plugin.STATUS_DEAD
        return value

    def execute(self, context, *args, **kws):
        """执行逻辑
        :param context: 上下文对象,用于获取参数或者传递结果
        :param args: 参数列表
        :param kws: keyword参数列表
        """
        if self.status == Plugin.STATUS_UNPREPARED:
            raise PluginUnPreparedException(
                u"插件 '{}' 尚未初始化,不能执行".format(self.name))
        if self.status == Plugin.STATUS_DEAD:
            raise PluginAlreadyDeadException(
                u"插件 '{}' 已经被清理过了,不能执行".format(self.name))
        # 执行参数验证
        self._args_validator(*args, **kws)
        return self._execute(context, *args, **kws)

    def __repr__(self):
        return None


class DefaultArgsValidator(object):

    """默认的参数验证器
    """

    def __init__(self, rules):
        self._rules = rules
        if rules:
            self._rule_dict = {rule.name: rule for rule in rules}

    def __call__(self, *args, **kws):
        if not self._rules:
            return
        for rule, arg_value in zip(self._rules, args):
            rule.validate(arg_value)
        for arg_name, arg_value in kws.items():
            rule = self._rule_dict[arg_name]
            rule.validate(arg_value)


class DefaultConfigValidator(object):

    """默认的配置项验证器
    """

    def __init__(self, rules):
        self._rules = rules

    def __call__(self, config):
        if not self._rules or not config:
            return
        for rule in self._rules:
            section, item_name = rule.name.split(".")
            item_value = None
            if section in config:
                items = config[section]
                item_value = items[item_name]
            rule.validate(item_value)
            if item_value is None and not rule.required:
                config[section][item_name] = rule.default


class InvalidPluginException(GirlFriendSysException):

    """构建插件对象出错时抛出此异常
    """
    pass


class PluginUnPreparedException(GirlFriendSysException):

    """当插件未进行初始化时抛出此异常
    """
    pass


class PluginAlreadyPreparedException(GirlFriendSysException):

    """当插件已经被初始化时抛出此异常
    """
    pass


class PluginAlreadyDeadException(GirlFriendSysException):

    """当插件已经被清理时抛出此异常
    """
    pass


class PluginManager(object):

    """插件管理器,主要包含的功能:

            注册插件
            获取插件
            批量对插件进行初始化
            批量对插件进行清理
            替换插件

       plugin模块会提供一个默认的PluginManager实例
       并会在该实例上默认注册所有的内置插件和基于girlfriend.plugin这个namespace
       的第三方插件

       开发者可以自行创建自己的PluginManager实例,并自行约定插件规则,
       通过PluginManagerChain可以将多个PluginManager按照优先级拼接在一起
    """

    def __init__(self):
        self._plugins = {}

    def plugin(self, plugin_name):
        """获取指定的插件
        :param plugin_name: 插件名称
        :return: 插件对象
        """
        return self.__getitem__(plugin_name)

    def __getitem__(self, plugin_name):
        if plugin_name not in self._plugins:
            raise PluginNotFoundException(plugin_name)
        return self._plugins[plugin_name]

    def register(self, plugin):
        """将插件注册到容器中,相同名字的插件不允许被重复注册
           如果要替换插件,那么需要先将插件从容器中移除,然后再进行注册
        :param plugin: 要注册的插件对象
        """
        if plugin.name in self._plugins:
            raise PluginAlreadyRegisteredException(plugin.name)
        self._plugins[plugin.name] = plugin

    def sys_prepare(self, config, *plugin_names):
        """对所有插件进行初始化
        :param config: 配置信息
        :param plugin_names: 要初始化的插件名称,如果为空,那么默认初始化所有插件
        """
        if not plugin_names:
            plugin_names = self._plugins.keys()
        for plugin_name in plugin_names:
            self._plugins[plugin_name].sys_prepare(config)

    def sys_cleanup(self, config, *plugin_names):
        """对所有插件进行清理
        :param config: 配置信息
        :param plugin_names: 要清理的插件名称,如果为空,那么默认对所有插件进行清理操作
        """
        if not plugin_names:
            plugin_names = self._plugins.keys()
        for plugin_name in plugin_names:
            self._plugins[plugin_name].sys_cleanup(config)

    def remove(self, plugin_name):
        self.__delitem__(plugin_name)

    def __delitem__(self, plugin_name):
        """删除插件
        """
        if plugin_name not in self._plugins:
            raise PluginNotFoundException(plugin_name)
        del self._plugins[plugin_name]

    def replace(self, plugin):
        """如果插件不存在,那么对插件进行注册,如果插件已经存在
           那么删除旧有的插件,使用新的插件对象进行注册
        :param plugin: 插件对象
        """
        try:
            self.register(plugin)
        except PluginAlreadyRegisteredException:
            self.remove(plugin.name)
            self.register(plugin)


class PluginAlreadyRegisteredException(GirlFriendBizException):

    """向插件管理器注册插件,如果插件名称已经存在,那么抛出此异常
    """

    def __init__(self, plugin_name):
        GirlFriendBizException.__init__(
            self,
            u"插件 '{}' 已经被注册了".format(plugin_name))


class PluginNotFoundException(GirlFriendBizException):

    """从插件管理器中获取插件对象,如果找不到,那么抛出此异常
    """

    def __init__(self, plugin_name):
        GirlFriendBizException.__init__(
            self,
            u"插件 '{}' 不存在".format(plugin_name))


plugin_manager = PluginManager()


def register_entry_points_plugins(entry_point="girlfriend.plugin"):
    """将基于entry_point的第三方插件注册到默认管理器
       :param entry_point: 加载插件的entry_point
    """

    global plugin_manager

    third_party_plugin_mgr = extension.ExtensionManager(
        namespace=entry_point, invoke_on_load=False)

    for ext in third_party_plugin_mgr:
        plugin_object, plugin = ext.plugin, None

        # 插件对象类型
        if isinstance(plugin_object, Plugin):
            plugin = plugin_object

        # 模块类型
        elif isinstance(plugin_object, types.ModuleType):
            plugin = Plugin.wrap_module(plugin_object)

        # 函数类型
        elif isinstance(plugin_object, types.FunctionType):
            plugin = Plugin.wrap_function(
                ext.name, plugin_object.__doc__, plugin_object)

        # 类类型
        elif isinstance(plugin_object, (types.ClassType, types.TypeType)):
            plugin = Plugin.wrap_class(plugin_object)

        # 不被支持的插件类型
        else:
            raise InvalidPluginException(
                u"插件 '{}' 的类型 '{}'不被支持".format(
                    ext.name,
                    type(plugin_object).__name__)
            )

        plugin_manager.register(plugin)


def auto_register():
    """自动注册内置的插件和基于entry_point的第三方插件
    """
    register_entry_points_plugins()


# 默认自动注册
auto_register()


class PluginManagerChain(object):

    """插件管理器链,当需要从多个插件管理器中获取插件时
       可将多个管理器按照优先级的先后传递给该对象,然后就可以按照优先级获取插件了
       总之,行为类似于Python3.x中的collections.ChainMap
    """

    def __init__(self, *plugin_managers):
        """
        :param plugin_managers: 插件管理器列表, 优先级高的管理器在前
        """
        self._plugin_managers = plugin_managers

    def plugin(self, plugin_name):
        """从插件管理器链中获取插件对象
        :param plugin_name: 插件名称
        :return 优先级最高的插件对象
        """
        return self.__getitem__(plugin_name)

    def __getitem__(self, plugin_name):
        for pm in self._plugin_managers:
            try:
                return pm.plugin(plugin_name)
            except PluginNotFoundException:
                continue
        raise PluginNotFoundException(plugin_name)

    def sys_prepare(self, config, *plugin_names):
        """将chain中所有的PluginManager依次全部初始化
        :param config: 配置对象
        :param plugin_names: 要初始化的插件名称
        """
        if plugin_names:
            for plugin_name in plugin_names:
                self.plugin(plugin_name).sys_prepare(config)
        else:
            for plugin_mgr in self._plugin_managers:
                plugin_mgr.sys_prepare(config)

    def sys_cleanup(self, config, *plugin_names):
        """将chain中所有的PluginManager依次全部清理
        :param config: 配置对象
        :param plugin_names: 要初始化的插件名称
        """
        if plugin_names:
            for plugin_name in plugin_names:
                self.plugin(plugin_name).sys_cleanup(config)
        else:
            for plugin_mgr in self._plugin_managers:
                plugin_mgr.sys_cleanup(config)

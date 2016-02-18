# coding: utf-8

"""Plugin模块的测试用例
"""

import imp
import fixtures
from girlfriend.util.validating import Rule
from girlfriend.util.config import Config
from girlfriend.exception import InvalidArgumentException
from girlfriend.testing import GirlFriendTestCase
from girlfriend.plugin import (
    Plugin,
    PluginManager,
    PluginManagerChain,
    PluginAlreadyDeadException,
    PluginAlreadyPreparedException,
    PluginUnPreparedException,
    InvalidPluginException,
    PluginAlreadyRegisteredException,
    PluginNotFoundException,
    DefaultArgsValidator,
    DefaultConfigValidator,
)


class PluginTestCase(GirlFriendTestCase):

    """plugin.Plugin类的测试用例
    """

    def test_lifecycle(self):
        """测试Plugin的构造和生命周期
        """
        plugin = Plugin(
            name="testing",
            description="testing plugin",
            execute=lambda ctx, arg: "execute {}".format(arg),
            sys_prepare=lambda config: "sys_prepare",
            sys_cleanup=lambda config: "sys_cleanup",
            args_validator=None,
            config_validator=None
        )

        self.assertEquals(plugin.sys_prepare(None), "sys_prepare")
        self.assertEquals(plugin.execute(None, "cat"), "execute cat")
        self.assertEquals(plugin.sys_cleanup(None), "sys_cleanup")

        # 已经cleanup之后再去执行会抛出PluginAlreadyDeadException
        self.failUnlessException(
            PluginAlreadyDeadException,
            Plugin.execute,
            plugin, None, "cat")

        # 重复执行sys_prepare操作会抛出PluginAlreadyPreparedException
        self.failUnlessException(
            PluginAlreadyPreparedException,
            Plugin.sys_prepare,
            plugin, None)

        plugin = Plugin(
            name="testing",
            description="testing plugin",
            execute=lambda ctx, arg: "execute {}".format(arg),
            sys_prepare=lambda config: "sys_prepare",
            sys_cleanup=lambda config: "sys_cleanup",
            args_validator=None,
            config_validator=None
        )

        # 尚未执行初始化时执行会抛出PluginUnPreparedException
        self.failUnlessException(
            PluginUnPreparedException,
            Plugin.execute,
            plugin, None, "cat")

        # 尚未执行初始化时清理会抛出PluginUnPreparedException
        self.failUnlessException(
            PluginUnPreparedException,
            Plugin.sys_cleanup,
            plugin, None)

    def test_wrap_function(self):
        """测试wrap_function类方法
        """

        # 只包装一个execute函数的时候
        plugin = Plugin.wrap_function(
            "testing",
            "testing plugin",
            lambda ctx, arg: "execute {}".format(arg))
        self.failUnlessException(
            PluginUnPreparedException,
            Plugin.execute,
            plugin, None, "cat")
        plugin.sys_prepare(None)
        self.assertEquals(plugin.execute(None, "cat"), "execute cat")
        plugin.sys_cleanup(None)
        self.failUnlessException(
            PluginAlreadyDeadException,
            Plugin.execute,
            plugin, None)

        # 包装错误的函数对象
        self.failUnlessException(
            InvalidPluginException,
            Plugin.wrap_function,
            "testing",
            "testing plugin",
            lambda: "hello"
        )

        self.failUnlessException(
            InvalidPluginException,
            Plugin.wrap_function,
            "testing",
            "testing plugin",
            lambda ctx: "execute",
            lambda config, args: "sys_prepare"
        )

        plugin = Plugin.wrap_function(
            "testing",
            "testing plugin",
            lambda ctx, arg: "execute {}".format(arg),
            lambda config: "sys_prepare a = {}".format(config["plugin"]["a"]),
            lambda config: "sys_cleanup",
            (Rule("arg", required=True, type=str, min=3, max=10),),
            (Rule("plugin.a", required=True, type=int, min=1, max=3),)
        )

        cfg = Config({"plugin": {"a": -1}})
        self.failUnlessException(
            InvalidArgumentException, plugin.sys_prepare, cfg)
        cfg = Config({"plugin": {"a": 1}})
        self.assertEquals(plugin.sys_prepare(cfg), "sys_prepare a = 1")
        self.assertEquals(plugin.execute(None, "cat"), "execute cat")
        self.failUnlessException(
            InvalidArgumentException, plugin.execute, None, "c")
        self.assertEquals(plugin.sys_cleanup(None), "sys_cleanup")

    def test_wrap_class(self):
        """测试wrap_class类方法
        """

        class TestPlugin(object):

            """testing plugin"""

            def __init__(self, a, b):
                self.a = a
                self.b = b

            def execute(self, context, arg):
                return "execute {0} {1}".format(arg, self.a + self.b)

            def sys_prepare(self, config):
                return "sys_prepare"

            def sys_cleanup(self, config):
                return "sys_cleanup"

        plugin = Plugin.wrap_class(TestPlugin, a=1, b=2)

        self.assertEquals(plugin.name, "TestPlugin")
        self.assertEquals(plugin.description, "testing plugin")
        self.assertEquals(plugin.sys_prepare(None), "sys_prepare")
        self.assertEquals(plugin.execute(None, "cat"), "execute cat 3")
        self.assertEquals(plugin.sys_cleanup(None), "sys_cleanup")

        # 复制一个TestPlugin并替换掉execute方法,检测参数错误
        test_plugin = type("TestPluginA", tuple(), dict(TestPlugin.__dict__))

        def execute(self):
            return "execute"

        setattr(test_plugin, "execute", execute)
        self.failUnlessException(
            InvalidPluginException,
            Plugin.wrap_class,
            test_plugin, 1, 2
        )

        test_plugin = type("TestPluginB", tuple(), dict(TestPlugin.__dict__))

        def sys_prepare(self, config, x):
            return "sys_prepare"

        setattr(test_plugin, "sys_prepare", sys_prepare)
        self.failUnlessException(
            InvalidPluginException,
            Plugin.wrap_class,
            test_plugin, 1, 2
        )

        # 测试名称属性
        test_plugin = type("TestPluginC", tuple(), dict(TestPlugin.__dict__))
        test_plugin.name = "hehe"
        plugin = Plugin.wrap_class(test_plugin, 1, 2)
        self.assertEquals(plugin.name, "hehe")

    def test_wrap_module(self):
        """测试wrap_module类方法
        """
        plugin_module = imp.new_module("test_plugin")
        plugin_module.execute = lambda ctx, arg: "execute {}".format(arg)

        plugin = Plugin.wrap_module(plugin_module)
        self.assertEquals(plugin.name, "test_plugin")

        plugin.sys_prepare(None)
        self.assertEquals(plugin.execute(None, "cat"), "execute cat")

        plugin_module.execute = lambda: "execute"
        self.failUnlessException(
            InvalidPluginException,
            Plugin.wrap_module,
            plugin_module
        )


class PluginManagerTestCase(GirlFriendTestCase):

    """PluginManager类的测试用例
    """

    def setUp(self):
        self.plugin_manager = PluginManager()

        self.plugin_a = Plugin.wrap_function(
            "test_plugin_a", "testing plugin a", lambda ctx: "execute a")
        self.plugin_b = Plugin.wrap_function(
            "test_plugin_b", "testing plugin b", lambda ctx: "execute b")

        self.plugin_manager.register(self.plugin_a)
        self.plugin_manager.register(self.plugin_b)

    def test_register(self):
        """测试注册类对象
        """
        self.plugin_manager.sys_prepare(None, "test_plugin_a")

        plugin_a = self.plugin_manager["test_plugin_a"]
        self.assertEquals(plugin_a.execute(None), "execute a")

        # 未进行初始化插件
        plugin_b = self.plugin_manager["test_plugin_b"]
        self.failUnlessException(
            PluginUnPreparedException,
            Plugin.execute,
            plugin_b, None)

        # 测试重复注册
        self.failUnlessException(
            PluginAlreadyRegisteredException,
            PluginManager.register,
            self.plugin_manager, self.plugin_a
        )

    def test_remove(self):
        """测试将插件移除
        """
        del self.plugin_manager["test_plugin_a"]
        self.failUnlessException(
            PluginNotFoundException,
            PluginManager.remove,
            self.plugin_manager, "test_plugin_a")
        self.failUnlessException(
            PluginNotFoundException,
            PluginManager.plugin,
            self.plugin_manager, "test_plugin_a")

    def test_replace(self):
        """测试插件替换
        """
        plugin_a = Plugin.wrap_function(
            "test_plugin_a",
            "testing plugin a",
            lambda ctx: "execute new a")
        self.plugin_manager.replace(plugin_a)
        self.plugin_manager.sys_prepare(None)
        self.assertEquals(
            self.plugin_manager["test_plugin_a"].execute(None),
            "execute new a")


class PluginManagerChainTestCase(GirlFriendTestCase):

    """PluginManagerChain测试用例
    """

    def test_getitem(self):
        plugin_a = Plugin.wrap_function(
            "test_plugin_a",
            "testing plugin a",
            lambda ctx: "execute a"
        )

        plugin_b = Plugin.wrap_function(
            "test_plugin_b",
            "testing plugin b",
            lambda ctx: "execute b"
        )

        plugin_manager_a = PluginManager()
        plugin_manager_a.register(plugin_a)
        plugin_manager_a.register(plugin_b)

        plugin_a1 = Plugin.wrap_function(
            "test_plugin_a",
            "testing plugin a 1",
            lambda ctx: "execute a 1"
        )

        plugin_manager_b = PluginManager()
        plugin_manager_b.register(plugin_a1)

        plugin_mgr_chain = PluginManagerChain(
            plugin_manager_b, plugin_manager_a)
        plugin_mgr_chain.sys_prepare(None)

        # 优先获取最优先的插件
        self.assertEquals(
            plugin_mgr_chain["test_plugin_a"].execute(None), "execute a 1")
        self.assertEquals(
            plugin_mgr_chain["test_plugin_b"].execute(None), "execute b")

        self.failUnlessException(
            PluginNotFoundException,
            PluginManagerChain.plugin,
            plugin_mgr_chain, "test_plugin_c")


# Plugin 相关Fixture

class PluginMgrFixture(fixtures.Fixture):

    """创建一个新的PluginManager并添加几个简单插件
    """

    def __init__(self, config, *plugins):
        if plugins:
            self._plugins = plugins
        else:
            self._plugins = [
                Plugin.wrap_function(
                    "plugin_a", "plugin a", lambda ctx: "plugin a"),
                Plugin.wrap_function(
                    "plugin_b", "plugin b", lambda ctx: "plugin b")
            ]
        self._config = config

    @property
    def plugin_manager(self):
        return self._plugin_manager

    def setUp(self):
        self._plugin_manager = PluginManager()
        for plugin in self._plugins:
            self._plugin_manager.register(plugin)
        self._plugin_manager.sys_prepare(self._config)

    def cleanUp(self):
        self._plugin_manager.sys_cleanup(self._config)


class DefaultArgsValidatorTestCase(GirlFriendTestCase):

    """默认参数验证器测试用例
    """

    def test_validate(self):
        rules = (
            Rule("id", type=int, required=True, min=10000, max=20000),
            Rule("name", type=str, required=False, min=2, max=6),
            Rule("email", type=str, required=True, logic=lambda value:
                 u"existed!" if value == "chz@gmail.com" else None)
        )
        validator = DefaultArgsValidator(rules)

        validator(15000, "SamChi", "sam@163.com")
        validator(15000, name=None, email="sam@163.com")

        self.failUnlessException(InvalidArgumentException,
                                 validator, 1, "SamChi", "aaaa")
        self.failUnlessException(InvalidArgumentException,
                                 validator, id=1, name=None, email="a")
        self.failUnlessException(InvalidArgumentException,
                                 validator, 10000, None, "chz@gmail.com")


class DefaultConfigValidatorTestCase(GirlFriendTestCase):

    """默认配置验证器测试用例
    """

    def test_validate(self):
        rules = (
            Rule("smtp.host", type=str, required=True),
            Rule("smtp.port", type=int, required=False, min=25, max=65535),
            Rule("smtp.user", type=str, required=True,
                 min=1, max=10, regex=r"^\w+$"),
            Rule("smtp.password", type=str, required=True, min=6, max=20),
            Rule("db.host", type=str, required=True, logic=lambda value:
                 None if value.startswith("192.168") else "Invalid!")
        )
        validator = DefaultConfigValidator(rules)

        cfg = Config({
            "smtp": {
                "host": "192.168.100.2",
                "port": 25,
                "user": "SamChi",
                "password": "123456"
            },
            "db": {
                "host": "192.168.1.1"
            }
        })
        validator(cfg)

        cfg["db"]["host"] = "localhost"
        self.failUnlessException(InvalidArgumentException, validator, cfg)

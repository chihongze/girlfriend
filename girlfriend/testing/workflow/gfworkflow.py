# coding: utf-8

"""本模块为gfworkflow中各个组件的测试用例
"""

from girlfriend.util.logger import (
    create_logger,
    stdout_handler,
)
from girlfriend.exception import (
    InvalidArgumentException,
    UnknownWitchToExecuteException
)
from girlfriend.plugin import Plugin, PluginManager
from girlfriend.testing.plugin import PluginMgrFixture
from girlfriend.testing import GirlFriendTestCase
from girlfriend.workflow.protocol import (
    End,
    OkEnd,
    AbstractListener
)
from girlfriend.workflow.gfworkflow import (
    Context,
    Job,
    Decision,
    MainThreadFork,
    MainThreadJoin,
    Workflow
)


class ContextTestCase(GirlFriendTestCase):

    def test_get_and_set(self):
        ctx = Context(None, {}, {}, None, None)
        ctx["a"] = 1
        self.assertEquals(ctx["a"], 1)
        self.assertEquals(ctx.get("a"), 1)
        self.assertIs(ctx["b"], None)


class JobTestCase(GirlFriendTestCase):

    def test_execute(self):
        """测试Job运行
        """
        plugin_mgr_fixture = PluginMgrFixture(None)
        self.useFixture(plugin_mgr_fixture)
        plugin_mgr = plugin_mgr_fixture.plugin_manager

        plugin = Plugin.wrap_function(
            "test_job", "test job", lambda ctx, a, b, c: a + b + c)
        plugin_mgr.register(plugin)
        plugin_mgr.sys_prepare(None, "test_job")

        def add_one(ctx, x):
            ctx["a"] += x

        plugin = Plugin.wrap_function("add_one", "add one", add_one)
        plugin_mgr.register(plugin)
        plugin_mgr.sys_prepare(None, "add_one")

        ctx = Context(None, {}, {}, plugin_mgr, None)

        job = Job(
            "test_job",
            args=(1, 2, 3)
        )

        self.assertEquals(job.execute(ctx), 6)

        # 当上下文中的参数是列表时，上下文中的参数取代列表
        ctx = Context(None, {}, {"test_job": (-1, -2, -3)}, plugin_mgr, None)
        self.assertEquals(job.execute(ctx), -6)

        # 测试使用上下文中的变量

        ctx = Context(None, {}, {
            "test_job": ("$a", "$b", "$c")
        }, plugin_mgr, None)

        ctx["a"], ctx["b"], ctx["c"] = 5, 6, 7
        self.assertEquals(job.execute(ctx), 5 + 6 + 7)

        # 字符串
        ctx = Context(None, {}, {
            "test_job": ("a", "b", "cd")
        }, plugin_mgr, None)
        self.assertEquals(job.execute(ctx), "abcd")

        # 字典参数
        job = Job(
            "test_job",
            args={
                "a": 1,
                "b": 2,
                "c": 3
            }
        )

        ctx = Context(None, {}, {}, plugin_mgr, None)
        self.assertEquals(job.execute(ctx), 6)

        # 如果context中同样包含参数，那么基于原先参数执行update操作
        ctx = Context(None, {}, {"test_job": {"a": -1}}, plugin_mgr, None)
        self.assertEquals(job.execute(ctx), 4)

        # 替换Context中的参数
        ctx = Context(None, {}, {"test_job": {
            "a": "$a",
            "b": "$b",
            "c": "$c"
        }}, plugin_mgr, None)

        ctx["a"], ctx["b"], ctx["c"] = -1, -2, -3
        self.assertEquals(job.execute(ctx), -6)

        # 初始化参数类型与上下文参数类型不一致时，抛出InvalidArgumentException
        ctx = Context(None, {}, {"test_job": ("a", "b", "c")},
                      plugin_mgr, None)
        self.failUnlessException(InvalidArgumentException, Job.execute,
                                 job, ctx)

        # 同时指定了插件和可执行逻辑时抛出异常
        self.failUnlessException(
            UnknownWitchToExecuteException,
            Job,
            "test_plugin",
            plugin="test_plugin",
            caller=lambda ctx: "hehe"
        )

        # 仅指定可执行逻辑时的情况
        job = Job("hehe", caller=lambda ctx, a, b, c: a * b * c)
        ctx = Context(None, {}, {"hehe": (5, 2, 3)}, plugin_mgr, None)
        self.assertEquals(job.execute(ctx), 30)

        # generator args

        def gen_args(context):
            for i in xrange(10):
                yield i,
        ctx = Context(None, {}, {}, plugin_mgr, None)
        ctx["a"] = 0

        job = Job("hehe", plugin="add_one", args=gen_args)
        job.execute(ctx)
        self.assertEquals(ctx["a"], sum(xrange(0, 10)))


class WorkflowTestCase(GirlFriendTestCase):

    def setUp(self):
        # 构建测试所需要的插件
        plugin_mgr = PluginManager()

        def add_one(ctx, num):
            return num + 1
        add_one_plugin = Plugin.wrap_function("add_one", "add one", add_one)
        plugin_mgr.register(add_one_plugin)

        def add_two(ctx, num):
            return num + 2
        add_two_plugin = Plugin.wrap_function("add_two", "add two", add_two)
        plugin_mgr.register(add_two_plugin)

        def add_three(ctx, num):
            value = num + 3
            ctx["add_three"] = value
        add_three_plugin = Plugin.wrap_function(
            "add_three", "add three", add_three)
        plugin_mgr.register(add_three_plugin)

        def division(ctx, a, b):
            return a / b
        division_plugin = Plugin.wrap_function(
            "division", "division", division)
        plugin_mgr.register(division_plugin)

        def add_four(ctx, num):
            if num < 0:
                raise InvalidArgumentException("num must more than zero!")
            return num + 4
        add_four_plugin = Plugin.wrap_function(
            "add_four", "add four", add_four)
        plugin_mgr.register(add_four_plugin)

        plugin_mgr.sys_prepare(None)
        self.plugin_mgr = plugin_mgr

    def test_execute_common(self):
        # 测试普通运行时的情况
        worklist = (
            Job("add_one"),
            Job("add_three", args=("$add_one.result",)),
            Decision("judge",
                     lambda ctx: "test_end"
                     if ctx["add_three"] > 5 else "add_two"),
            Job("add_two", args={"num": "$add_three"}, goto="end"),
            OkEnd("test_end", execute=lambda ctx: ctx["add_three"])  # 自定义end
        )

        workflow = Workflow(worklist, None, self.plugin_mgr)
        end = workflow.execute(args={"add_one": (1,)})
        self.assertEquals(end.result, 7)

        end = workflow.execute(args={"add_one": {"num": 10}})
        self.assertEquals(end.result, 14)

    def test_execute_fork(self):
        logger = create_logger("gf", (stdout_handler(),))
        worklist = (
            Job("add_one"),
            MainThreadFork("fork"),
            Job("add_three", args=("$add_one.result",)),
            MainThreadJoin("join", join=lambda ctx: ctx["add_three"])
        )
        workflow = Workflow(worklist, None, self.plugin_mgr, logger=logger)
        end = workflow.execute(args={"add_one": [1]})
        self.assertIsNone(end.result)  # 写入的是thread local上下文，而非全局上下文

        def save_to_parrent(ctx):
            ctx.parrent["add_three"] = ctx["add_three"]

        worklist = (
            Job("add_one"),
            MainThreadFork("fork"),
            Job("add_three", args=("$add_one.result",)),
            Job("collect", caller=save_to_parrent),
            MainThreadJoin("join", join=lambda ctx: ctx["add_three"])
        )
        workflow = Workflow(worklist, None, self.plugin_mgr, logger=logger)
        end = workflow.execute(args={"add_one": [1]})
        self.assertEquals(end.result, 5)

    def test_execute_with_exception(self):
        # 测试异常发生时的情况
        worklist = (
            Job("add_one", args=(5, )),
            Job("division", args={"a": "$add_one.result"})
        )

        workflow = Workflow(worklist, None, self.plugin_mgr)
        end = workflow.execute(args={
            "division": {"b": 3}
        })
        self.assertEquals(end.result, 2)

        # 除0错误
        end = workflow.execute(args={
            "division": {"b": 0}
        })
        self.assertEquals(end.status, End.STATUS_ERROR_HAPPENED)
        self.assertEquals(end.exc_type, ZeroDivisionError)

    def test_execute_with_invalid_args(self):
        # 测试错误请求参数
        worklist = (
            Job("add_four"),
        )

        workflow = Workflow(worklist, None, self.plugin_mgr)
        end = workflow.execute(args={"add_four": (1, )})
        self.assertEquals(end.result, 5)

        end = workflow.execute(args={"add_four": (-1, )})
        self.assertEquals(end.status, End.STATUS_BAD_REQUEST)

    def test_add_listener(self):
        listener = ListenerA(0)
        worklist = (
            Job("add_one"),
            Job("add_two", args=("$add_one.result",)),
            Decision("decide", lambda ctx: "add_three"
                     if ctx["add_two.result"] > 10 else "division"),
            Job("add_three", args=("$add_two.result",)),
            OkEnd("add_three_end", execute=lambda ctx: ctx["add_three"]),
            Job("division", args=("$add_two.result", 2))
        )

        workflow = Workflow(worklist, None, self.plugin_mgr)
        workflow.add_listener(listener)
        workflow.add_listener(ListenerB)

        end = workflow.execute(args={"add_one": (1, )})
        self.assertEquals(end.result, 2)
        self.assertEquals(listener.a, -4)

        listener.a = 0
        end = workflow.execute(args={"add_one": (10, )})
        self.assertEquals(end.result, 16)
        self.assertEquals(listener.a, -5)

        listener.a = 0
        end = workflow.execute(args={
            "add_one": (1, ),
            "division": ("$add_two.result", 0)
        })
        self.assertEquals(end.status, End.STATUS_ERROR_HAPPENED)
        self.assertEquals(listener.a, -2)
        self.assertEquals(end.exc_type, ZeroDivisionError)


class ListenerA(AbstractListener):

    def __init__(self, a):
        self.a = a

    def on_start(self, ctx):
        print "\n> listener a on workflow start"
        ctx["a"] = self.a

    def on_unit_start(self, ctx):
        print "> listener a enter unit {}".format(ctx.current_unit)
        self.a += 1

    def on_unit_finish(self, ctx):
        print "> listener a finish unit {}".format(ctx.current_unit)
        self.a -= 2

    def on_finish(self, ctx):
        print "> listener a on workflow finish"
        ctx["a_finish"] = self.a + 1

    def on_error(self, ctx, exc_type, exc_value, tb):
        print "> error happened on unit {}".format(ctx.current_unit)
        self.exc_type = exc_type


class ListenerB(AbstractListener):

    def on_start(self, ctx):
        self.x = 0

    def on_unit_start(self, ctx):
        self.x += 1

    def on_finish(self, ctx):
        print "\n In listener B x is {}".format(self.x)

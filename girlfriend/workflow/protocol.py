# coding: utf-8

"""本模块规范了workflow各个组件所需满足的接口形式，
在girlfriend中，一个完整的workflow由以下组件构成:

   Start       任务执行的起始点，列表中的第一个Job默认为起始点

   Job         任务执行的基本逻辑单元

   Decision    决策单元，当工作流有多个逻辑分支时
               对上一步的执行结果进行判断，决定接下来运行的Job

   Fork        分支单元，会启用一个新的线程/进程/协程来运行接下来的步骤

   Join        分支汇聚单元，等待所有Fork出的线程完成，并将结果聚合在一起

   End         任务结束点，携带执行状态和最终返回结果

   Context     上下文对象，用于在工作流的不同Job之间传递数据

   Workflow    工作流本身，包含要执行的工作流描述以及具体的执行逻辑

   Listener    分为针对单个Job的事件监听和针对整个workflow的工作监听
"""

import traceback
import collections
import itertools
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty
)
from girlfriend.exception import InvalidArgumentException
from girlfriend.util.lang import args2fields
from girlfriend.util.config import Config


class WorkflowUnit(object):

    """工作流单元抽象
       Start Job Decision WaitFor End隶属于工作流单元
    """
    __metaclass__ = ABCMeta

    @abstractproperty
    def name(self):
        """workflow中的每一个单元都要有一个独一无二的名字
        """
        pass

    @abstractproperty
    def unittype(self):
        """工作单元类型
        """
        pass

    @abstractmethod
    def execute(self, context):
        """执行该单元的具体逻辑
           该方法由执行引擎进行回调
        """
        pass


class AbstractJob(WorkflowUnit):

    """任务执行单元抽象
    """

    __metaclass__ = ABCMeta

    @property
    def unittype(self):
        return "job"

    @abstractproperty
    def goto(self):
        pass


class AbstractDecision(WorkflowUnit):

    """决策单元抽象
    """

    __metaclass__ = ABCMeta

    @property
    def unittype(self):
        return "decision"


class AbstractFork(WorkflowUnit):

    """Fork单元抽象
    """

    __metaclass__ = ABCMeta

    @property
    def unittype(self):
        return "fork"

    @abstractproperty
    def start_point(self):
        pass

    @abstractproperty
    def end_point(self):
        pass

    @abstractmethod
    def execute(self, units, parrent_context, parrent_listeners=None):
        pass


class AbstractJoin(WorkflowUnit):

    """Join单元抽象
    """

    __metaclass__ = ABCMeta

    @property
    def unittype(self):
        return "join"

    @abstractmethod
    def execute(self, context):
        pass


class End(WorkflowUnit):

    """结束单元
    """

    STATUS_OK = 0  # 一切顺利,任务成功结束

    STATUS_BAD_REQUEST = 1  # 请求参数错误,任务无法执行

    STATUS_ERROR_HAPPENED = 2  # 服务出错

    def __init__(self, name, status, result=None, execute=None):
        self._name = name
        self._status = status
        self._result = result
        self._execute = execute

    @property
    def name(self):
        return self._name

    @property
    def unittype(self):
        return "end"

    @property
    def status(self):
        """状态码,描述本次工作流的执行结果
        """
        return self._status

    @property
    def result(self):
        """执行结果,工作流执行的最终汇总结果
        """
        return self._result

    def execute(self, context):
        if self._execute:
            self._result = self._execute(context)

    def __str__(self):
        return "<End name={name}, status={status}, result={result}>".format(
            name=self.name,
            status=self.status,
            result=self.result
        )


class OkEnd(End):

    """顺利执行时返回的结果
    """

    def __init__(self, name="end", result=None, execute=None):
        End.__init__(
            self,
            name=name,
            status=End.STATUS_OK,
            result=result,
            execute=execute
        )


class BadRequestEnd(End):

    """请求参数错误时的返回结果
    """

    def __init__(self, name="bad_request_end",
                 msg=None, result=None, execute=None):
        End.__init__(
            self,
            name=name,
            status=End.STATUS_BAD_REQUEST,
            result=result,
            execute=execute
        )
        self._msg = msg

    @property
    def msg(self):
        return self._msg


class ErrorEnd(End):

    """当出现程序异常时返回的结果
    """

    def __init__(self, exc_type, exc_value, tb,
                 name="error_end", result=None, execute=None):
        """
            :param exc_type 异常类型
            :param exc_value 异常值
            :param tb 异常发生的traceback
        """
        End.__init__(
            self,
            name=name,
            status=End.STATUS_ERROR_HAPPENED,
            result=result,
            execute=execute
        )
        self._exc_type = exc_type
        self._exc_value = exc_value
        self._tb = tb

    @property
    def exc_type(self):
        return self._exc_type

    @property
    def exc_value(self):
        return self._exc_value

    @property
    def tb(self):
        return self._tb

    def print_exc(self):
        """打印异常
        """
        traceback.print_exception(self._exc_type, self._exc_value, self._tb)


class AbstractContext(collections.Mapping):

    """上下文抽象
       上下文由执行引擎在每次执行之前选择具体类型进行创建
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        super(AbstractContext, self).__init__()

    @abstractproperty
    def config(self):
        """全局配置
        """
        pass

    @abstractproperty
    def logger(self):
        """获取日志对象
        """
        pass

    @abstractproperty
    def current_unit(self):
        """当前工作流正执行的单元名称
        """
        pass

    @abstractproperty
    def current_unittype(self):
        """当前执行单元类型
        """
        pass

    @abstractmethod
    def args(self, job_name):
        """获取某个工作流的执行参数
        """
        pass

    @abstractmethod
    def plugin(self, plugin_name):
        """获取插件对象
        """
        pass

    @abstractproperty
    def plugin_mgr(self):
        """插件管理器
        """
        pass

    @abstractproperty
    def parrent(self):
        """获取父级上下文对象
        """
        pass

    @abstractproperty
    def thread_id(self):
        pass


class AbstractWorkflow(object):

    """工作流抽象
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def add_listener(self, listener):
        """添加监听器
        """
        pass

    @abstractmethod
    def execute(self, start_point=None, args=None):
        """开始执行工作流
           :param start_point 指定运行的起始点
           :param args 工作流执行参数
           :return 返回一个End对象，描述执行结果
        """
        pass


class AbstractListener(object):

    """工作流监听器，此处定义了所有可监听的事件
       可以有选择感兴趣的事件进行监听
    """

    EVENTS = (
        "on_start",
        "on_unit_start",
        "on_unit_finish",
        "on_interrupt",
        "on_interrupt_now",
        "on_error",
        "on_finish"
    )

    @classmethod
    def wrap_function(cls, event_funcs):
        """将一个函数对象包装成一个监听器对象
           :param event_funcs 由事件名和函数对象所构成的元组
                  例如("on_start", start_func, "on_job_start", job_start_func)
        """
        return _WrappedFunctionListener(event_funcs)

    def __init__(self):
        pass

    def on_start(self, context):
        """在工作流调用了start方法之后立即进行
        """
        pass

    def on_unit_start(self, context):
        """在开始执行一个新的job时执行此方法
        """
        pass

    def on_unit_finish(self, context):
        """当一个Job被顺利完成时，执行此方法
           当因错误而结束时，不会执行此方法
        """
        pass

    def on_error(self, context,
                 exc_type, exc_value, traceback):
        """当工作流出现异常时，执行此方法
        """
        pass

    def on_finish(self, context):
        """当工作流顺利结束时，执行此方法
           当因错误而结束时，不会执行此方法
        """
        pass

    def __repr__(self):
        return "<Workflow event listener:{class_name} @ {id}>".format(
            class_name=self.__class__.__name__,
            id=id(self)
        )

    def __str__(self):
        return self.__repr__()


class _WrappedFunctionListener(AbstractListener):

    """用以包装函数的监听器类
    """

    def __init__(self, event_funcs):
        super(_WrappedFunctionListener, self).__init__()

        if len(event_funcs) % 2 != 0:
            raise InvalidArgumentException((
                u"event_funcs元数不正确，"
                u"必须为(事件名1, 函数1, 事件名2, 函数2, ...)的形式"))
        for event_name, func in itertools.izip(
                event_funcs[::2], event_funcs[1::2]):
            if not event_name.startswith("on_"):
                event_name = "on_" + event_name

            if event_name not in AbstractListener.EVENTS:
                raise InvalidArgumentException(u"未知的事件：{}".format(event_name))

            def event_handler_factory(func):
                def event_handler(ctx, f=func):
                    return f(ctx)

                return event_handler

            setattr(self, event_name, event_handler_factory(func))


class Env(object):

    """环境对象，用于描述工作流当前所运行的环境，比如测试环境、正式环境
       不同环境可携带不同的参数
    """

    @classmethod
    def test_env(cls):
        return cls("test", {}, Config(), u"测试环境")

    @args2fields(False)
    def __init__(self, name, args=None, config=None, description=""):
        """
        :param name 环境名称，比如test
        :param args 该环境的参数
        :param config 该环境当前的配置
        :param description 环境描述
        """
        if args is None:
            self._args = {}
        if config is None:
            self._config = {}

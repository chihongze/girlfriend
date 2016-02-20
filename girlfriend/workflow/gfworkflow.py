# coding: utf-8

"""GirlFriend自带的Workflow实现
"""

import sys
import types
from girlfriend.exception import (
    GirlFriendBizException,
    InvalidArgumentException,
    UnknownWitchToExecuteException
)
from girlfriend.util.lang import (
    DelegateMeta,
    SequenceCollectionType,
    parse_context_var,
)
from girlfriend.util.logger import (
    create_logger,
    stdout_handler,
)
from girlfriend.workflow.protocol import (
    AbstractContext,
    AbstractJob,
    AbstractDecision,
    AbstractWorkflow,
    OkEnd,
    ErrorEnd,
    BadRequestEnd,
    AbstractListener
)
from girlfriend.plugin import plugin_manager


class Context(AbstractContext):

    """基于本地内存的上下文实现
    """

    __metaclass__ = DelegateMeta

    # 以下方法将代理到字典类
    delegate_methods = [
        "__contains__",
        "__delitem__",
        "__len__",
        "__setitem__",
        "get",
        "__iter__",
    ]

    def __init__(self, config, args, plugin_mgr, logger):
        super(Context, self).__init__()
        self.delegate = {}
        self._config = config
        self._current_unit = None
        if args is None:
            self._args = {}
        else:
            self._args = args
        self._plugin_mgr = plugin_mgr
        self._logger = logger

    def __getitem__(self, property):
        return self.delegate.get(property, None)

    @property
    def config(self):
        """配置对象
        """
        return self._config

    def logger(self):
        """获取Logger对象
        """
        return self._logger

    @property
    def current_unit(self):
        """当前正在进行的工作单元名称
        """
        return self._current_unit

    @current_unit.setter
    def current_unit(self, current_unit):
        self._current_unit = current_unit

    @property
    def current_unittype(self):
        """当前正在进行的工作单元类型
        """
        return self._current_unittype

    @current_unittype.setter
    def current_unittype(self, current_unittype):
        self._current_unittype = current_unittype

    def args(self, job_name):
        """获取某个job运行所需要的参数
        """
        return self._args.get(job_name, None)

    def plugin(self, plugin_name):
        return self._plugin_mgr.plugin(plugin_name)

    def __str__(self):
        return "<Context args={args}, config={config}, ctx={ctx}>".format(
            args=self._args,
            config=self._config,
            ctx=self.delegate
        )


class Job(AbstractJob):

    """最基本的任务单元实现
    """

    def __init__(self, name, plugin=None, caller=None, args=None, goto=None):
        """
          :param name   任务名称，在整个工作流中唯一供跳转声明使用
          :param plugin 使用的插件名称，如果不指定，在没有caller的情况下，任务名称将作为插件名称
          :param caller 可执行逻辑，在不使用插件的时候可以指定一个函数来作为任务逻辑
                        如果同时指定了caller和plugin，那么会抛出UnknowWitchToExecute异常
          :param args   执行插件所需要的参数，可以不指定，在运行时再具体指定
          :param goto   执行完毕后的下一步任务名，可以不指定，自动取任务链上下一个位置
        """

        self._name = name

        # 两者都有指定，抛出异常
        if plugin and caller:
            raise UnknownWitchToExecuteException(
                u"Job '{}' 不能同时指定caller和plugin".format(self._name)
            )

        # 两者都未指定，那么插件名称默认为Job的名称
        if not plugin and not caller:
            self._plugin_name = name
        else:
            self._plugin_name = plugin

        self._caller = caller
        self._args = args
        self._goto = goto

    @property
    def name(self):
        return self._name

    @property
    def plugin_name(self):
        return self._plugin_name

    @property
    def goto(self):
        return self._goto

    @goto.setter
    def goto(self, goto):
        self._goto = goto

    def execute(self, context):

        # 将函数类型参数展开
        if isinstance(self._args, types.FunctionType):
            self._args = self._args(context)

        # 如果是字符串类型，那么以上下文中的属性作为参数列表
        if isinstance(self._args, types.StringTypes):
            if self._args.startswith("$"):
                self._args = context[self._args[1:]]
            else:
                self._args = context[self._args]

        # 如果是生成器，那么迭代执行任务
        if isinstance(self._args, types.GeneratorType):
            return [self._execute(context, template_args)
                    for template_args in self._args]
        else:
            return self._execute(context, self._args)

    def _execute(self, context, template_args):
        args = self._get_runtime_args(context, template_args)

        # 获取可执行对象
        executable = self._get_executable(context)

        result = None
        if args is None:
            result = executable(context)
        elif isinstance(args, SequenceCollectionType):
            result = executable(context, *args)
        elif isinstance(args, types.DictType):
            result = executable(context, **args)

        # 自动将插件计算结果写入Context
        context["{}.result".format(self.name)] = result
        return result

    def _get_executable(self, context):
        if self._caller:
            return self._caller
        plugin = context.plugin(self._plugin_name)
        return plugin.execute

    def _get_runtime_args(self, context, template_args):
        """获取运行时参数
           Job的参数分为两部分，一部分是在workflow声明时指定的参数
           一部分是在运行时通过context指定的参数

           参数支持两种形式，一种是参数列表，一种是字典关键字的形式

           如果是列表，那么将会用context中的列表取代self._args中的列表
           如果是字典，那么将会执行update操作，context中的项将覆盖_args中的项
           如果self._args为None，那么直接使用context中的参数
           如果self._args与context类型不一致，那么抛出异常

           最终将args中的字符串变量名用Context真实值进行替换
        """

        context_args = context.args(self.name)
        if isinstance(context_args, types.FunctionType):
            context_args = context_args(context)

        if isinstance(context_args, types.StringTypes):
            if context_args.startswith("$"):
                context_args = context[context_args[1:]]
            else:
                context_args = context[context_args]

        args_schema = None
        if not context_args:
            args_schema = template_args
        elif not template_args:
            args_schema = context_args
        elif isinstance(template_args, SequenceCollectionType):
            if not isinstance(context_args, SequenceCollectionType):
                raise InvalidArgumentException(
                    u"Job '{}'的初始参数类型跟上下文指定的参数类型不一致".format(self.name)
                )
            args_schema = template_args
            if context_args:
                args_schema = context_args
        elif isinstance(template_args, types.DictType):
            if not isinstance(context_args, types.DictType):
                raise InvalidArgumentException(
                    u"Job '{}'的初始参数类型跟上下文指定的参数类型不一致".format(self.name)
                )
            args_schema = template_args
            if context_args:
                args_schema = dict(template_args)
                args_schema.update(context_args)
        else:
            raise InvalidArgumentException(u"只能接受列表、元组、字典类型的参数对象")

        # 替换为真正的变量
        if not args_schema:
            return None
        elif isinstance(args_schema, SequenceCollectionType):
            return [parse_context_var(context, arg) for arg in args_schema]
        elif isinstance(args_schema, types.DictType):
            return {arg_name: parse_context_var(context, args_schema[arg_name])
                    for arg_name in args_schema}


class Decision(AbstractDecision):

    """判断节点的实现
    """

    def __init__(self, name, decide_logic):
        """
            :param name 节点名称
            :param decide_logic 判断逻辑，接受一个context参数，
                                对当前工作流的状态进行判断并返回下一步要执行的节点名称
        """
        self._name = name
        self._decide_logic = decide_logic

    @property
    def name(self):
        return self._name

    def execute(self, context):
        return self._decide_logic(context)


class Workflow(AbstractWorkflow):

    """无状态的本地工作流执行引擎实现
    """

    def __init__(self, workflow_list, config,
                 plugin_mgr=plugin_manager, context_factory=Context,
                 logger=None):
        """
        :param workflow_list 工作单元列表
        :param config 配置数据
        :param plugin_mgr 插件管理器，默认是plugin自带的entry_points管理器
        :param context_factory 上下文工厂，必须具有config, args, plugin_mgr, parent
                               这四个约定的参数
        :param logger 日志对象
        """

        self._workflow_list = workflow_list
        self._config = config
        self._plugin_manager = plugin_mgr

        self._units = {}  # 以名称为Key的工作流单元引用字典
        for idx, unit in enumerate(self._workflow_list):
            if unit.name in self._units:
                raise WorkflowUnitExistedException(unit.name)
            self._units[unit.name] = unit
            if unit.unittype == "job":
                # 如果未指定goto，那么goto的默认值是下一个节点
                if unit.goto is None:
                    if idx < len(self._workflow_list) - 1:
                        unit.goto = self._workflow_list[idx + 1].name
                    else:
                        unit.goto = "end"
        self._context_factory = context_factory
        self._listeners = []

        # 创建logger
        if logger is None:
            self._logger = create_logger("girlfriend", (stdout_handler(),))
        else:
            self._logger = logger

    def add_listener(self, listener=None, **kws):
        """为工作流添加监听器，该方法有两种使用方式。

           直接使用: 直接传递一个监听器对象或者一个AbstractListener子类的类型对象
                    当传递监听器对象时，此对象会在每次进行execute时重复使用。
                    当传递类型对象时，每次进行execute都会依照此类型生成一个新的对象
                    类型对象的构造函数参数除self以外必须为空。
           包装函数: 只传递感兴趣的生命周期
                    workflow.add_listener(start=on_start, finish=on_finish)
        """
        if listener:
            if (not isinstance(listener, AbstractListener) and
                    not issubclass(listener, AbstractListener)):
                raise InvalidArgumentException(
                    u"监听器必须是AbstractListener对象或者是其子类类型对象")
            self._listeners.append(listener)
            return
        if kws:
            event_funcs = []
            for event_name in kws:
                if not event_name.startswith("on_"):
                    event_name = "on_" + event_name
                if event_name not in AbstractListener.EVENTS:
                    raise InvalidArgumentException(u"不被支持的事件:" + event_name)
                event_funcs += (event_name, kws[event_name])
            self._listeners.append(AbstractListener.wrap_function(event_funcs))
            return

    def execute(self, args=None, start_point=None):
        """执行工作流
           :param start_point 工作流起始点，如果为None，
                              那么将从workflow_list第一个元素开始执行
           :param args 运行时参数
        """
        if start_point:
            start_unit = self._units[start_point]
        else:
            start_unit = self._workflow_list[0]

        # 构建上下文
        ctx = self._context_factory(
            config=self._config,
            args=args,
            plugin_mgr=self._plugin_manager,
            logger=self._logger
        )
        listener_objects = {}  # 用来保存每次执行时需要创建新对象的listener

        self._logger.info(u"工作流开始执行，起始点为 '{}'".format(start_unit.name))

        # 执行初始化的listener
        self._execute_listeners("on_start", ctx, listener_objects)

        current_unit = start_unit
        last_result = None
        goto = None
        while True:
            ctx.current_unit = current_unit.name
            ctx.current_unittype = current_unit.unittype

            # 进入新的Unit
            self._logger.info(u"开始执行工作单元 {} [{}]".format(
                current_unit.name, current_unit.unittype))

            self._execute_listeners("on_unit_start", ctx, listener_objects)

            try:
                if current_unit.unittype == "job":
                    last_result = current_unit.execute(ctx)
                    goto = current_unit.goto
                elif current_unit.unittype == "decision":
                    goto = current_unit.execute(ctx)
                elif current_unit.unittype == "fork":
                    pass
                elif current_unit.unittype == "end":
                    # 用户指定的结束节点
                    current_unit.execute(ctx)
                    self._execute_listeners("on_unit_finish",
                                            ctx, listener_objects)
                    self._execute_listeners("on_finish", ctx, listener_objects)
                    self._logger.info(u"工作流顺利执行完毕")
                    return current_unit
            except InvalidArgumentException as e:
                self._logger.exception(u"单元参数错误")
                exc_type, exc_value, tb = sys.exc_info()
                self._execute_on_error_listeners(ctx,
                                                 exc_type, exc_value, tb,
                                                 listener_objects)
                return BadRequestEnd(msg=unicode(e))
            except Exception:
                self._logger.exception(u"系统错误，工作流被迫中止")
                exc_type, exc_value, tb = sys.exc_info()
                self._execute_on_error_listeners(ctx,
                                                 exc_type, exc_value, tb,
                                                 listener_objects)
                return ErrorEnd(exc_type, exc_value, tb)  # 返回错误的结果
            else:
                # 执行完成事件
                self._execute_listeners("on_unit_finish",
                                        ctx, listener_objects)
                self._logger.info(u"工作单元 {} [{}] 执行完毕".format(
                    current_unit.name, current_unit.unittype))
                if goto == "end":
                    self._execute_listeners("on_finish", ctx, listener_objects)
                    self._logger.info(u"工作流顺利执行完毕")
                    return OkEnd(result=last_result)  # 将最后一个单元的结果作为默认返回的结果
                else:
                    current_unit = self._units[goto]  # 处理下一个单元

    def _execute_listeners(self, event_name, context, listener_objects):
        """遍历执行监听器
        """
        for idx, listener in enumerate(self._listeners):
            if isinstance(listener, AbstractListener):
                getattr(listener, event_name)(context)
            elif issubclass(listener, AbstractListener):
                listener_obj = self.__create_listener_obj(
                    idx, listener, listener_objects)
                getattr(listener_obj, event_name)(context)

    def _execute_on_error_listeners(self, context,
                                    exc_type, exc_value, tb, listener_objects):
        """遍历执行错误监听器
        """
        for idx, listener in enumerate(self._listeners):
            if isinstance(listener, AbstractListener):
                listener.on_error(context, exc_type, exc_value, tb)
            elif issubclass(listener, AbstractListener):
                listener_obj = self.__create_listener_obj(
                    idx, listener, listener_objects)
                listener_obj.on_error(
                    context, exc_type, exc_value, tb)

    def __create_listener_obj(self, idx, listener_class, listener_objects):
        listener_obj = listener_objects.get(idx)
        if not listener_obj:
            listener_obj = listener_class()
            listener_objects[idx] = listener_obj
        return listener_obj


class WorkflowUnitExistedException(GirlFriendBizException):

    def __init__(self, unit_name):
        super(WorkflowUnitExistedException, self).__init__(
            u"工作单元 '{}' 已经存在".format(unit_name))

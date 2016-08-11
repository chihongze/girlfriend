# coding: utf-8
import types
from girlfriend.workflow.gfworkflow import (
    Workflow,
    Context
)
from girlfriend.util.lang import ObjDictModel
from girlfriend.util.config import Config
from girlfriend.plugin import plugin_mgr


class WorkflowBuilder(object):

    def __init__(self):
        self._clazz = Workflow
        self._options = ObjDictModel()
        self._units = tuple()
        self._plugin_mgr = plugin_mgr
        self._config = Config()
        self._context_factory = Context
        self._listeners = tuple()
        self._logger = None

    def build(self):

        # 如果工作单元是函数类型，那么使用options对其展开
        if isinstance(self._units, types.FunctionType):
            self._units = self._units(self._options)

        workflow = self._clazz(
            self._units,
            config=self._config,
            plugin_mgr=self._plugin_mgr,
            context_factory=self._context_factory,
            logger=self._logger
        )
        if self._listeners:
            for listener in self._listeners:
                workflow.add_listener(listener)

        return workflow

    def clazz(self, clazz):
        """工作流类对象
        """
        self._clazz = clazz
        return self

    def options(self, options):
        """生成工作流单元序列的选项
        """
        self._options = options
        return self

    def units(self, units):
        """工作流单元列表
        """
        self._units = units
        return self

    def plugin_mgr(self, plugin_mgr):
        """插件管理器
        """
        self._plugin_mgr = plugin_mgr
        return self

    def config(self, config):
        """配置信息
        """
        self._config = config
        return self

    def context_factory(self, context_factory):
        """上下文工厂
        """
        self._context_factory = context_factory
        return self

    def listeners(self, listeners):
        """监听器
        """
        self._listeners = listeners
        return self

    def logger(self, logger):
        """日志对象
        """
        self._logger = logger
        return self

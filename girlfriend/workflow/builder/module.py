# coding: utf-8

from __future__ import absolute_import

import types
from girlfriend.workflow.builder import WorkflowBuilder
from girlfriend.workflow.gfworkflow import Workflow
from girlfriend.plugin import plugin_mgr
from girlfriend.util.config import Config
from girlfriend.util.lang import ObjDictModel


class ModuleWorkflowBuilder(WorkflowBuilder):

    def __init__(self, module, config=None, options=None):
        super(self, ModuleWorkflowBuilder).__init__()

        # 从模块中加载各属性
        self._clazz = getattr(module, "workflow_class", Workflow)
        self._units = getattr(module, "workflow")
        self._plugin_mgr = getattr(module, "plugin_manager", plugin_mgr)
        self._options = options if options else ObjDictModel()

        self._config = config if config is not None else Config()
        module_config = getattr(module, "config", None)
        # 使用模块中的配置去覆盖之前的配置
        if module_config is not None:
            if isinstance(module_config, types.FunctionType):
                module_config = module_config(options)
            self._config.update(module_config)

        self._logger = getattr(module, "logger", None)
        self._listeners = getattr(module, "listeners", tuple())  # 获取监听器列表

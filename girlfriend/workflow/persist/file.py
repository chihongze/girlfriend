# coding: utf-8

"""本模块提供基于文件持久化操作的抽象
"""

from __future__ import absolute_import

import os.path
from abc import ABCMeta, abstractmethod
from girlfriend.workflow.protocol import AbstractListener
from girlfriend.workflow.persist import (
    RecoverInfo,
    RecoverPolicy,
    WorkflowFinishedException
)
from girlfriend.workflow.gfworkflow import Context

STATUS_RUNNING = 1  # 工作流正在执行
STATUS_FINISHED = 2  # 工作流已经成功完成


class AbstractFilePersistListener(AbstractListener):

    __metaclass__ = ABCMeta

    def __init__(self, dump_to="dump.dat"):
        self._dump_to = dump_to

    def on_unit_start(self, context):
        """在每个任务单元正式开始之前，都会将当前上下文对象dump下来。
           在Fork中执行的单元除外
        """
        # 确保只dump主工作流的单元
        if context.thread_id is None:
            self._dump_context(context, STATUS_RUNNING)
            context.logger.debug(u"Dump context to '{}' success.".format(
                self._dump_to))
        else:
            context.logger.debug(
                "Dump ignore '{}'.".format(context.current_unit))

    def on_finish(self, context):
        """在整个工作流结束的时候记录完成状态，处于完成状态的工作流无需恢复中断
        """
        if context.thread_id is None:
            self._dump_context(context, STATUS_FINISHED)
        else:
            context.logger.debug(
                "Dump ignore '{}'.".format(context.current_unit))

    def _dump_context(self, context, status):
        with open(self._dump_to, "w") as f:
            self._dump_data_to_file({
                "data": context.delegate,
                "current_unit": context.current_unit,
                "current_unittype": context.current_unittype,
                "status": status
            }, f)

    @abstractmethod
    def _dump_data_to_file(self, data, file):
        pass


class AbstractFileRecoverPolicy(RecoverPolicy):

    def __init__(self, recover_from):
        self._recover_from = recover_from

    def load(self):
        if not os.path.exists(self._recover_from):
            # 持久化文件不存在，无需恢复
            return RecoverInfo(None, Context)

        with open(self._recover_from, "r") as f:
            dumped_data = self._load_data(f)

        if dumped_data["status"] == STATUS_FINISHED:
            # 工作流已经完成，无需恢复
            raise WorkflowFinishedException(
                u"'{}'中被持久化的工作流已经处于完成状态。".format(self._recover_from))

        def _context_factory(
                parrent=None, config=None, args=None,
                plugin_mgr=None, logger=None, thread_id=None, data=None):

            _data = {}
            _data.update(dumped_data["data"])
            if data is not None:
                _data.update(data)

            ctx = Context(
                parrent=parrent,
                config=config,
                args=args,
                plugin_mgr=plugin_mgr,
                logger=logger,
                thread_id=thread_id,
                data=_data
            )
            return ctx

        return RecoverInfo(
            dumped_data["current_unit"],
            _context_factory
        )

    @abstractmethod
    def _load_data(self, file):
        pass

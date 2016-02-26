# coding: utf-8

from __future__ import absolute_import

import sys
import types
import threading
from concurrent.futures import ThreadPoolExecutor
from girlfriend.util.lang import args2fields, SequenceCollectionType
from girlfriend.exception import InvalidArgumentException
from girlfriend.workflow.protocol import AbstractJob
from girlfriend.workflow.gfworkflow import Job


class BufferingJob(Job):

    """提供缓冲功能的工作单元
       该工作单元拥有时间和数目两个限制
       该单元会一直处于阻塞状态，直到缓冲的对象达到了指定的数目或者阻塞超过了指定的时间
    """

    def __init__(self, name, plugin=None, caller=None, args=None,
                 max_items=10, timeout=None, filter=None,
                 immediately=False, give_back_handler=None, goto=None):
        """
        :param name 工作单元名称
        :param plugin 使用插件名称
        :param caller 执行逻辑
        :param args 参数
        :param max_items 最大条目
        :param timeout 超时时间
        :param filter 过滤器，接受一个context参数和一个条目，返回True or False
        :param immediately 如果超时，是否立即结束工作，
                           如果为True，那么会造成正在处理的数据丢失，但是会准时停止。
                           如果为False，那么会等待当前任务完成再继续，
                           但如果目前正在遭遇IO阻塞之类的情况，会继续阻塞很长时间。
        :param give_back_handler 用于处理immediately为True时丢失的数据，比如重新归还到队列等等。
        :param goto 下一步要执行的工作单元
        """
        Job.__init__(self, name, plugin, caller, args, goto)
        self._max_items, self._timeout = max_items, timeout
        self._filter = filter
        self._immediately = immediately
        self._give_back_handler = give_back_handler
        if self._timeout is not None and self._timeout < 0:
            raise InvalidArgumentException(u"timeout参数必须是大于等于0的整数，单位是秒")

    def execute(self, context):
        self._expand_args(context)

        timeout_lock = threading.Lock()
        t = BufferingJob._Executor(self, context, timeout_lock)
        t.start()
        if self._timeout:
            t.join(self._timeout)
            t.finished = True
            if not self._immediately:
                with timeout_lock:
                    pass
        else:
            t.join()
        result = t.result
        context["{}.result".format(self._name)] = result
        return result

    class _Executor(threading.Thread):

        """该类将Job的执行状态封装到一个单独的对象中，避免循环执行Job时造成状态污染
        """

        def __init__(self, job, context, timeout_lock):
            threading.Thread.__init__(self)
            self.job = job
            self.context = context
            self.timeout_lock = timeout_lock
            self.finished = False
            self._result = []
            self.copy_result_lock = threading.Lock()
            self._finally_result = self._result

        def run(self):
            while len(self._result) < self.job._max_items:
                if self.finished:
                    self._finish()
                    return
                if self.job._timeout and not self.job._immediately:
                    with self.timeout_lock:
                        # 该锁用于timeout的场景，避免遗漏正在执行的中的任务
                        self._filter_and_append()
                else:
                    self._filter_and_append()
            else:
                self._finish()

        def _filter_and_append(self):
            record = self.job._execute(self.context, self.job._args)
            if self.job._filter is None or self.job._filter(record):
                self._result.append(record)

        def _finish(self):
            if self.finished:
                if (
                    self.job._immediately and
                    self.job._give_back_handler is not None
                ):
                    with self.copy_result_lock:
                        if len(self._finally_result) < len(self._result):
                            for r in self._result[len(self._finally_result):]:
                                self.job._give_back_handler(self.context, r)

        @property
        def result(self):
            if (
                self.job._immediately and
                self.job._give_back_handler is not None
            ):
                with self.copy_result_lock:
                    self._finally_result = self._result[::]
            return self._finally_result


class ConcurrentJob(AbstractJob):

    """基于PoolExecutor的并行任务单元
    """

    @args2fields()
    def __init__(
            self, name, sub_jobs, pool=None,
            pool_type=ThreadPoolExecutor, join=None,
            error_action="stop", error_handler=None, error_default_value=None,
            goto=None):
        """
        :param name 并行单元名称
        :param sub_jobs 子任务列表
        :param pool 指定池对象，若为None，那么会依据pool_type构建一个新的pool
        :param pool_type 池类型，如果pool为None，根据该类型来构建新的pool
        :param join 对最终结果进行处理，接受context对象和每个任务的结果列表作为参数
        :param error_action 错误处理动作，如果是stop，那么会终止整个工作流，
                            如果是continue，那么会忽略该错误继续工作流
        :param error_handler 错误处理器，当使用continue时，不会触发全局的error listener
                             可在此指定单独的error_handler进行处理
        :param error_default_value 当处于continue的错误处理模式时，出错任务的默认值
        :param goto 下一步要执行的单元
        """
        if self._error_action != "stop" and self._error_action != "continue":
            raise InvalidArgumentException(u"错误处理动作只允许stop或者continue类型")

    @property
    def name(self):
        """任务单元名称
        """
        return self._name

    @property
    def plugin_name(self):
        """插件名称列表
        """
        plugin_names = {}
        for sub_job in self._sub_jobs:
            if isinstance(sub_job.plugin_name, (tuple, list, set)):
                plugin_names.update(sub_job.plugin_name)
            elif sub_job.plugin_name is not None:
                plugin_names.add(sub_job.plugin_name)
        return list(plugin_names)

    @property
    def goto(self):
        return self._goto

    @goto.setter
    def goto(self, goto):
        self._goto = goto

    def execute(self, context):
        """并行执行所有任务单元
        """
        # 初始化池
        if self._pool is None:
            pool = self._pool_type(len(self._sub_jobs))
        else:
            pool = self._pool

        # 提交子任务，获取Future列表
        futures = [pool.submit(sub_job.execute, context)
                   for sub_job in self._sub_jobs]

        # 获取执行结果
        all_result = []
        for future in futures:
            result = None
            try:
                result = future.result()
            except Exception as e:
                context.logger.exception(
                    u"并行任务'{}'的子任务运行出错，处理方式为：'{}'".format(
                        self.name, self._error_action))
                if self._error_action == "stop":
                    # rethrow异常，中断工作流
                    raise e
                elif self._error_action == "continue":
                    # 调用用户自定义error_handler
                    if self._error_handler is not None:
                        exc_type, exc_value, tb = sys.exc_info()
                        self._error_handler(context, exc_type, exc_value, tb)
                    # 被忽略任务的结果作为None添加到结果列表
                    all_result.append(self._error_default_value)
            else:
                all_result.append(result)

        if self._pool is None:
            pool.shutdown()  # 关闭线程池

        if self._join is not None:
            all_result = self._join(context, all_result)

        context["{}.result".format(self._name)] = all_result
        return all_result


def _expand_sub_results(ctx, result):
    new_result = []
    for r in result:
        if isinstance(r, SequenceCollectionType):
            new_result.extend(r)
        else:
            new_result.append(r)
    return new_result


class ConcurrentForeachJob(Job):

    """针对一组参数，单个plugin/caller的并行执行单元
    """

    def __init__(self, name, plugin=None, caller=None, args=None,
                 thread_num=10, task_num_per_thread=None,
                 pool_type=ThreadPoolExecutor, sub_join=None,
                 result_join=_expand_sub_results, error_action="stop",
                 error_handler=None, error_default_value=None,
                 goto=None):
        """
        :param name 工作单元名称
        :param plugin 插件名称
        :param caller 执行逻辑
        :param args 参数
        :param thread_num 线程数目，默认开启10个线程
        :param task_num_per_thread 每线程任务数，主要用于不可预知总数的生成器参数
        :param pool_type 池对象类型
        :param sub_join 针对每组线程的join逻辑，接受一个Context对象和一个结果列表作为参数
        :param result_join 对最终的结果进行处理，接受一个Context对象和各个Task的结果列表
        :param error_action 错误处理动作，如果是stop，那么会终止整个工作流的执行
                            如果是continue，那么会忽略错误继续执行
        :param error_handler 错误处理器，如果错误处理动作为continue，那么不会调用上层workflow
                             的错误监听器，而是会调用此处的错误处理器
        :param error_default_value 如果是error_action为continue，那么会以该默认值作为错误操作默认结果
        :param goto 要执行的下一个工作单元
        """
        Job.__init__(self, name, plugin, caller, args, goto)
        self._thread_num = thread_num
        self._task_num_per_thread = task_num_per_thread
        self._pool_type, self._sub_join = pool_type, sub_join
        self._result_join, self._error_action = result_join, error_action
        self._error_handler = error_handler
        self._error_default_value = error_default_value

        if self._error_action != "stop" and self._error_action != "continue":
            raise InvalidArgumentException(u"错误处理动作只允许stop或者continue类型")

        try:
            len(args)
        except TypeError:
            if self._task_num_per_thread is None:
                raise InvalidArgumentException(
                    u"args参数为无法预知长度的类型，无法自动分配任务，"
                    u"请使用task_num_per_thread参数来为每个线程分配任务数目"
                )
        else:
            # 根据参数总数目计算每个线程应该分配的任务数
            if self._task_num_per_thread is None:
                args_len = len(self._args)
                if args_len % self._thread_num == 0:
                    self._task_num_per_thread = args_len / self._thread_num
                else:
                    self._task_num_per_thread = args_len / self._thread_num + 1

        self._error_break = False  # 错误中断标记

    def execute(self, context):
        context.logger.info((
            "Concurrent foreach job '{}' begin, "
            "the thread pool size is {}, task/thread is {}"
        ).format(self._name, self._thread_num, self._task_num_per_thread))
        pool = self._pool_type(self._thread_num)
        sub_args = []
        futures = []
        try:
            if isinstance(self._args,
                          (types.FunctionType, types.GeneratorType)):
                self._args = self._args()
            for idx, arg in enumerate(self._args, start=1):
                sub_args.append(arg)
                if idx % self._task_num_per_thread == 0:
                    futures.append(
                        pool.submit(
                            ConcurrentForeachJob._execute,
                            self, context, sub_args)
                    )
                    sub_args = []
            else:
                if sub_args:
                    futures.append(
                        pool.submit(ConcurrentForeachJob._execute,
                                    self, context, sub_args)
                    )
        finally:
            pool.shutdown()

        # 等待futures
        results = [f.result() for f in futures]

        if self._result_join is not None:
            results = self._result_join(context, results)

        context["{}.result".format(self._name)] = results
        return results

    def _execute(self, context, sub_args):
        executable = self._get_executable(context)
        results = []
        for args in sub_args:
            if self._error_break:  # 检查任务是否已被中断
                return
            try:
                result = None
                if args is None:
                    result = executable(context)
                elif isinstance(args, SequenceCollectionType):
                    result = executable(context, *args)
                elif isinstance(args, types.DictType):
                    result = executable(context, **args)
            except Exception as e:
                context.logger.exception(
                    u"并行任务'{}'的子任务运行出错，处理方式为：'{}'".format(
                        self.name, self._error_action))
                if self._error_action == "stop":
                    # rethrow异常，中断工作流
                    self._error_break = True  # 标记任务已中断
                    raise e
                elif self._error_action == "continue":
                    # 调用用户自定义error_handler
                    if self._error_handler is not None:
                        exc_type, exc_value, tb = sys.exc_info()
                        self._error_handler(context, exc_type, exc_value, tb)
                    # 被忽略任务的结果作为None添加到结果列表
                    results.append(self._error_default_value)
            else:
                results.append(result)

        if self._sub_join is not None:
            return self._sub_join(context, results)
        return results

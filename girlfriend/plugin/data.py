# coding: utf-8

"""数据转换插件抽象
"""

from abc import (
    ABCMeta,
    abstractmethod
)


class AbstractDataHandler(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def __call__(self, context):
        pass

    def _handle_record(self, record, collector=None):
        """处理记录
        :param record 记录
        :param collector 收集器，回调函数或者方法，比如list.append，set.add
        """
        # 执行过滤器
        if self._record_filter is not None:
            if not self._record_filter(record):
                return

        # 对行进行数据转换
        if self._record_handler is not None:
            record = self._record_handler(record)

        if collector is not None:
            collector(record)

        return record


class AbstractDataReader(AbstractDataHandler):

    __metaclass__ = ABCMeta

    def _handle_result(self, context, result):
        """对最终结果进行包装
        """
        if self._result_wrapper is not None:
            result = self._result_wrapper(result)
        if self._variable:
            context[self._variable] = result
        return result


class AbstractDataWriter(AbstractDataHandler):

    __metaclass__ = ABCMeta

    pass

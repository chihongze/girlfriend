# coding: utf-8

"""CSV读取与写入插件
"""

from __future__ import absolute_import

import types
import csv
import StringIO
import requests
from girlfriend.util.lang import args2fields
from girlfriend.util.resource import HTTP_SCHEMA
from girlfriend.plugin.data import (
    AbstractDataReader,
    AbstractDataWriter
)


class CSVReaderPlugin(object):

    name = "read_csv"

    def execute(self, context, *csv_readers):
        return [reader(context) for reader in csv_readers]


class CSVR(AbstractDataReader):

    """
    CSV读单元，以单个CSV文件为单位
    """

    @args2fields()
    def __init__(self, path=None, content=None,
                 record_handler=None, record_filter=None, result_wrapper=None,
                 dialect="excel", variable=None):
        """
        :param path csv文件路径，可以是文件路径，也可以是url地址
        :param content csv数据内容，指定了content就不需要指定了path了，反之亦然
        :param record_handler 记录处理器，接受解析后的行对象
        :param record_filter 对解析后的行对象进行过滤
        :param result_wrapper 对最终结果的包装器
        :param dialect csv方言，可以是字符串也可以是csv.Dialect对象
        :param variable context中的引用变量名
        """
        pass

    def __call__(self, context):
        # get Dialect object
        if isinstance(self._dialect, types.StringTypes):
            dialect = csv.get_dialect(self._dialect)

        # get content
        content = self._content
        if self._content is None:
            if self._path.startswith(HTTP_SCHEMA):
                content = requests.get(self._path).text
            else:
                with open(self._path, "r") as f:
                    content = f.read()

        if isinstance(content, types.StringTypes):
            content = StringIO.StringIO(content)

        result = []
        csv_reader = csv.reader(content, dialect=dialect)
        for row in csv_reader:
            self._handle_record(row, result.append)

        return self._handle_result(context, result)


class CSVWriterPlugin(object):

    name = "write_csv"

    def execute(self, context, *csv_writers):
        return [writer(context) for writer in csv_writers]


class CSVW(AbstractDataWriter):

    """
    CSV写单元，以单个CSV文件为单位
    """

    @args2fields()
    def __init__(self, path, object, record_handler=None,
                 record_filter=None, dialect="excel"):
        """
        :param path 写入文件路径，如果是以memory:开头，只将CSV内容保存到变量中
        :param object 将要转换为csv格式的可迭代对象
        :param record_handler 行对象转换，将记录转换为适合csv输出的格式
        :param record_filter 行过滤器，对行记录进行过滤
        :param dialect 方言，可接受字符串格式的方言名称或者Dialect对象
        """
        pass

    def __call__(self, context):

        if isinstance(self._object, types.StringTypes):
            self._object = context[self._object]

        # get dialect object
        if isinstance(self._dialect, types.StringTypes):
            dialect = csv.get_dialect(self._dialect)

        if self._path.startswith("memory:"):
            buffer_ = StringIO.StringIO()
            self._write_object(buffer_, dialect)
            buffer_.seek(0)
            context[self._path[len("memory:"):]] = buffer_
        else:
            with open(self._path, "w") as f:
                self._write_object(f, dialect)
        return self._path

    def _write_object(self, f, dialect):
        csv_writer = csv.writer(f, dialect=dialect)
        for row_obj in self._object:
            row_obj = self._handle_record(row_obj)
            if not row_obj:
                continue
            csv_writer.writerow(row_obj)

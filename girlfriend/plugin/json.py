# coding: utf-8

"""json读写插件
"""

import re
import types
import ujson
import requests
from girlfriend.util.lang import args2fields
from girlfriend.util.resource import HTTP_SCHEMA
from girlfriend.plugin.data import (
    AbstractDataReader,
    AbstractDataWriter
)
from girlfriend.exception import InvalidArgumentException


class JSONReaderPlugin(object):

    """可以从文件或者Web URL中加载json对象，并进行格式转换
       支持常见的json文件格式
    """

    name = "read_json"

    def execute(self, context, *json_readers):
        return [reader(context) for reader in json_readers]


JSON_REGEX = re.compile(r"\{.*?\}")


class JSONR(AbstractDataReader):

    @args2fields()
    def __init__(self, path, style,
                 record_handler=None, record_filter=None, result_wrapper=None,
                 variable=None):
        """
        :param  context 上下文对象
        :param  path  加载路径，可以是文件路径，也可以是web url
        :param  style  json数据格式，允许三种格式：
                        1. line: 文件每行是一个json对象
                        2. array: 文件内容是一个json数组
                        3. extract:property 文件是一个json对象，但是只提取某一部分进行处理
                        4. block: 区块，不在同一行
        :param  record_handler  行处理器，返回的每行都是字典对象，通过该函数可以进行包装
                                如果返回None，那么将对该行忽略
        :param  record_filter   行过滤器
        :param  result_wrapper 对最终结果进行包装
        :param  variable  结果写入上下文的变量名，如果为None，那么将返回值交给框架自身来保存
        """
        pass

    def __call__(self, context):
        result = []

        # 基于文件的逐行加载
        if self._style == "line" and not self._path.startswith(HTTP_SCHEMA):
            with open(self._path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(("#", "//", ";")):
                        continue
                    record = ujson.loads(line)
                    self._handle_record(record, result.append)
        else:
            json_content = None
            # 从不同的来源加载json对象
            if self._path.startswith(HTTP_SCHEMA):
                json_content = requests.get(self._path).text
            else:
                with open(self._path, "r") as f:
                    json_content = f.read()

            json_content = json_content.strip()

            # 按行读取
            if self._style == "line":
                for line in json_content.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    record = ujson.loads(line)
                    self._handle_record(record, result.append)
            # 按块读取
            if self._style == "block":
                json_buffer = []
                in_block = False
                for char in json_content:
                    if char == "{":
                        in_block = True
                        json_buffer.append(char)
                    elif char == "}" and in_block:
                        json_buffer.append(char)
                        try:
                            record = ujson.loads("".join(json_buffer))
                        except ValueError:
                            continue
                        else:
                            self._handle_record(record, result.append)
                            json_buffer = []
                            in_block = False
                    elif in_block:
                        json_buffer.append(char)
            # 按数组读取
            elif self._style == "array":
                json_array = ujson.loads(json_content)
                for record in json_array:
                    self._handle_record(record, result.append)
            # 使用属性提取器
            elif self._style.startswith("extract:"):
                json_obj = ujson.loads(json_content)
                keys = self._style[len("extract:"):].split(".")
                for key in keys:
                    json_obj = json_obj[key]
                for record in json_obj:
                    self._handle_record(record, result.append)

        return self._handle_result(context, result)


class JSONWriterPlugin(object):

    name = "write_json"

    def execute(self, context, *json_writers):
        for json_writer in json_writers:
            json_writer(context)


class JSONW(AbstractDataWriter):

    @args2fields()
    def __init__(self, path, style, object,
                 record_handler=None, record_filter=None,
                 http_method="post", http_field=None, variable=None):
        """
        :param path 写入路径，默认为文件路径，如果是HTTP或者HTTPS开头，那么将会POST到对应的地址
        :param style 写入格式，line - 按行写入 array - 作为json数组写入 object - 作为单独对象写入
        :param table 要操作的对象，可以是具体的对象，也可以是context中的变量名
        :param record_handler 行处理器，可以在此进行格式转换，比如把时间对象转换为字符串
        :param record_filter 行过滤器
        :param http_method http写入方法，默认为POST，可以指定PUT
        :param variable 将json写入上下文变量
        """
        pass

    def __call__(self, context):
        if (self._style == "line" and self._path and
                not self._path.startswith(HTTP_SCHEMA)):
            with open(self._path, "w") as f:
                for row in self._object:
                    row = self._handle_record(row)
                    f.write(ujson.dumps(row) + "\n")
            return

        # json文本
        json_text = ""

        if isinstance(self._object, types.FunctionType):
            self._object = self._object(context)
        elif isinstance(self._object, types.StringTypes):
            self._object = context[self._object]

        if self._style == "object":
            json_text = ujson.dumps(self._object)

        result = []
        for row in self._object:
            row = self._handle_record(row, result.append)

        # 数组格式直接dump
        if self._style == "array":
            json_text = ujson.dumps(result)

        # line格式
        if self._style == "line":
            string_buffer = []
            for row in self._object:
                row = self._handle_record(row)
                string_buffer.append(ujson.dumps(row))
            json_text = "\n".join(string_buffer)

        if self._path is None:
            if self._variable:
                context[self._variable] = json_text
                return
            else:
                raise InvalidArgumentException(
                    u"当path为None时，必须指定一个有效的variable")

        if self._path.startswith(HTTP_SCHEMA):
            if self._http_method.lower() == "post":
                if self._http_field:
                    requests.post(
                        self._path, data={self._http_field: json_text})
                elif self._style == "line":
                    requests.post(self._path, data=json_text)
                else:
                    requests.post(self._path, json=json_text)
            elif self._http_method.lower() == "put":
                requests.put(self._path, json=json_text)
        else:
            with open(self._path, "w") as f:
                f.write(json_text)

        if self._variable:
            context[self._variable] = json_text

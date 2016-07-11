# coding: utf-8

"""该模块包含各Service所需要的domain model
"""

import datetime


class Result(object):

    """所有公开的服务接口返回的结果都是Result对象
    """

    CODE_OK = 200
    CODE_BAD_REQUEST = 400
    CODE_SERVICE_ERROR = 500

    @classmethod
    def ok(cls, reason=None, message=None, data=None):
        return cls(Result.CODE_OK, reason, message, data)

    @classmethod
    def bad_request(cls, reason=None, message=None, data=None):
        return cls(Result.CODE_BAD_REQUEST, reason, message, data)

    @classmethod
    def service_error(cls, reason=None, message=None, data=None):
        return cls(Result.CODE_SERVICE_ERROR, reason, message, data)

    def __init__(self, code, reason=None, message=None, data=None):
        """
        :param code 接口操作的结果状态码, 成功、请求有误、服务内部错误
        :param reason 使用简短的字符串来描述的错误原因，客户端可用该字段进行模式匹配
        :param message 消息，常用于表示错误消息
        :param data 接口返回的数据对象，为方便扩展，建议采用k-v格式
        """
        self._code = code
        self._reason = reason
        self._message = message
        self._data = data

    @property
    def code(self):
        return self._code

    @property
    def reason(self):
        return self._reason

    @property
    def message(self):
        return self._message

    @property
    def data(self):
        return self._data

    def is_ok(self):
        return self._code == Result.CODE_OK

    def is_bad_request(self):
        return self._code == Result.CODE_BAD_REQUEST

    def is_service_error(self):
        return self._code == Result.CODE_SERVICE_ERROR

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)


class WorkflowInfo(object):

    """该对象表示一个由daemon维护的工作流信息
    """

    def __init__(self, name, code_path, main_module, description,
                 file_hash, updated_on=None, created_on=None):
        """
        :param name 工作流的名称，在一个服务节点中，每个工作流的名称是唯一的
        :param code_path 工作流的代码路径，可以是一个python源码文件，也可以是一个包含众多源码文件的zip文件
        :param main_module 入口模块，执行系统会从该模块去加载任务
        :param description 工作流描述
        :param updated_on 更新时间
        :param created_on 创建时间
        """
        self._name = name
        self._code_path = code_path
        self._main_module = main_module
        self._description = description
        self._file_hash = file_hash
        now = datetime.datetime.now()
        self._updated_on = updated_on or now
        self._created_on = created_on or now

    @property
    def name(self):
        return self._name

    @property
    def code_path(self):
        return self._code_path

    @property
    def main_module(self):
        return self._main_module

    @property
    def description(self):
        return self._description

    @property
    def file_hash(self):
        return self._file_hash

    @property
    def updated_on(self):
        return self._updated_on

    @property
    def created_on(self):
        return self._created_on

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)

# coding: utf-8

"""用于模块操作的工具集合
"""

import imp
import os.path
import pkg_resources
from girlfriend.exception import InvalidArgumentException


def load_module(module_path, module_name=None, entry_point=None):
    """根据不同形式的module_path来对模块进行加载
       :param module_path
              如果以冒号开头，那么加载指定entry_point注册的模块
              如果以.py结尾，那么按照文件进行加载。
              其它情况按照当前PYTHONPATH中的模块名进行加载
       :return 如果加载成功，那么返回加载的模块对象
               如果加载失败，那么返回None
    """

    if module_path[0] == ":":
        # 加载entry_point模块
        if not entry_point:
            raise InvalidArgumentException(u"必须指定entry_point参数")
        module_path = module_path[1:]
        for ep in pkg_resources.iter_entry_points(entry_point):
            if ep.name == module_path:
                return ep.load()
        return None
    elif module_path.endswith(".py"):
        # 加载文件模块
        if module_name is None:
            module_name = os.path.split(module_path)[1].split(".")[0]
        if not os.path.exists(module_path):
            raise InvalidArgumentException(u"找不到模块文件 '{}'".format(module_path))
        return imp.load_source()
    else:
        # 按模块名称加载模块
        return __import__(module_path, fromlist=[""])

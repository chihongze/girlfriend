# coding: utf-8

"""很多时候我们经常需要定义目录文件的生成模板，比如生成一个配置文件的模板，
生成一个工程目录结构等等，该模块用于帮助轻松实现这类工作。
"""

import os
import os.path
from abc import (
    ABCMeta,
    abstractproperty,
    abstractmethod
)
from girlfriend.exception import GirlFriendBizException


class TemplateUnit(object):

    """模板单元抽象
    """

    __metaclass__ = ABCMeta

    TYPE_FILE = "file"

    TYPE_DIR = "dir"

    def __init__(self, name, access=None):
        """
          :param name 目录名或文件名
          :param access  文件权限，默认按照umask来，接受一个八进制数字，比如0666
        """
        self._name = name
        self._access = access

    @property
    def name(self):
        """单元名称
        """
        return self._name

    @property
    def access(self):
        return self._access

    @abstractproperty
    def unittype(self):
        """单元类型
        """
        pass

    @abstractmethod
    def makeme(self, base_dir=os.getcwd()):
        """创建该单元及其子元素
        """
        pass


class Dir(TemplateUnit):

    def __init__(self, name, access=None, elements=None):
        super(Dir, self).__init__(name, access)
        if elements:
            self.elements = elements
        else:
            self.elements = []

    @property
    def unittype(self):
        return TemplateUnit.TYPE_DIR

    def append(self, element):
        self.elements.append(element)

    def makeme(self, base_dir=os.getcwd()):
        # 先建自己
        myself_dir = os.path.join(base_dir, self.name)
        if os.path.exists(myself_dir):
            raise DirAlreadyExistException(
                u"目录 '{}' 已经存在了，不能重复创建".format(myself_dir))
        os.mkdir(myself_dir)
        if self.access:
            os.chmod(myself_dir, self.access)
        # 创建子元素
        for element in self.elements:
            element.makeme(myself_dir)


class File(TemplateUnit):

    def __init__(self, name, access=None, content=""):
        super(File, self).__init__(name, access)
        self._content = content

    @property
    def unittype(self):
        return TemplateUnit.TYPE_FILE

    def makeme(self, base_dir):
        myself_path = os.path.join(base_dir, self.name)
        if os.path.exists(myself_path):
            raise FileAlreadyExistException(
                u"文件 '{}' 已经存在了，不能重复创建".format(myself_path))
        with open(myself_path, "w") as f:
            f.write(self._content)
        if self.access:
            os.chmod(myself_path, self.access)


class DirAlreadyExistException(GirlFriendBizException):

    """当目录已经存在时，抛出此异常
    """
    pass


class FileAlreadyExistException(GirlFriendBizException):

    """当文件已经存在时，抛出此异常
    """
    pass

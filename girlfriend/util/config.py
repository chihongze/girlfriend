# coding: utf-8

"""配置解析相关
"""

import os
import os.path
import StringIO
import requests
from ConfigParser import SafeConfigParser
from girlfriend.exception import GirlFriendBizException

# 配置文件样例
CONFIG_EXAMPLE = """
[db_test]
connect_url=sqlite:///:memory:
"""


class Config(dict):

    """Config是一个Mapping实现，用于保存配置信息
    """

    @staticmethod
    def load_by_name(name="default"):
        """根据配置资源名称来加载配置数据
           :param name 资源名称，默认为default
        """
        default_config_path = os.path.join(
            os.environ["HOME"],
            ".gf",
            "gf.cfg"
        )
        if not os.path.exists(default_config_path):
            raise ConfigFileNotExistException(
                u"用户目录下的默认配置文件不存在，无法获取配置资源名称映射，"
                u"您可以尝试使用gf_config命令来初始化默认配置文件"
            )
        default_config = Config.load_from_file(default_config_path)
        if name == "default":
            return default_config
        config = default_config.get("config")
        if not config:
            raise UnknownConfigResourceException(
                u"找不到名称为{}的配置信息，请检查默认配置".format(name)
            )
        resource_path = config.get(name)
        if not resource_path:
            raise UnknownConfigResourceException(
                u"找不到名称为 '{}' 的配置信息，请检查默认配置".format(name)
            )
        if resource_path.startswith(("http://", "https://")):
            return Config.load_from_web(resource_path)
        else:
            return Config.load_from_file(resource_path)

    @staticmethod
    def load_from_file(file_path):
        """从文件中加载配置
           :param 文件路径
        """
        with open(file_path, "r") as f:
            return Config.wrap_fp(f)

    @staticmethod
    def load_from_web(url):
        """从web加载配置
           :param 会对该地址进行GET请求，请求获取的数据将作为配置文件
        """
        response = requests.get(url)
        return Config.wrap_fp(StringIO.StringIO(response.text))

    @classmethod
    def wrap_fp(cls, fp):
        """将一个文件描述符包装成Config对象
        """
        parser = SafeConfigParser()
        parser.readfp(fp)
        config = cls()
        for section_name in parser.sections():
            config[section_name] = cls(
                {name: value for name, value in parser.items(section_name)}
            )
        return config

    def __getattr__(self, key):
        if key not in self:
            raise AttributeError(u"属性 '{}' 不存在".format(key))
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def prefix(self, *pre):
        """根据Section前缀获取子配置项
        """
        return {section: self[section]
                for section in self if section.startswith(pre)}

    def get(self, section, item_name=None):
        if item_name is None:
            return dict.get(self, section)
        section_items = dict.get(self, section, {})
        if not section_items:
            return None
        return section_items.get(item_name)


class ConfigFileNotExistException(GirlFriendBizException):

    """当目标配置文件不存在时抛出此异常
    """
    pass


class UnknownConfigResourceException(GirlFriendBizException):

    """根据名称找不到对应的配置资源时抛出此异常
    """
    pass

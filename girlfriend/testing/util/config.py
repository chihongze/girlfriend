# coding: utf-8

"""针对config对象的测试用例
"""

import fixtures
from girlfriend.testing import GirlFriendTestCase
from girlfriend.util.config import Config


class ConfigTestCase(GirlFriendTestCase):

    def test_getsetattr(self):
        cfg = Config()
        cfg["a"] = 1
        self.assertEquals(cfg.a, 1)
        cfg.a = 2
        self.assertEquals(cfg.a, 2)
        cfg.b = Config()
        cfg.b.a = 3
        self.assertEquals(cfg.b.a, 3)


class ConfigLoadFixture(fixtures.Fixture):

    """加载默认配置文件 $HOME/.gf/gf.config
    """

    def setUp(self):
        self.config = Config.load_by_name("default")

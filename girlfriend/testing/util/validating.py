# coding: utf-8

"""lang.validating测试用例
"""

from numbers import Number
from girlfriend.util.validating import Rule
from girlfriend.exception import InvalidArgumentException
from girlfriend.testing import GirlFriendTestCase


class RuleTestCase(GirlFriendTestCase):

    def test_validate(self):

        def test_logic(value):
            if not isinstance(value, Number):
                return
            if value % 2 != 0:
                return u"{} 不能被2整除".format(value)

        test_rule = Rule(
            "test",
            type=(str, int),
            required=True,
            min=5,
            max=20,
            regex=r"^\d+$",
            logic=test_logic
        )

        # 正确通过验证的情况
        test_rule.validate("1" * 6)
        test_rule.validate(20)

        # 错误的类型
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, 1.1)

        # 错误的长度
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, "hehe")
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, 2)
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, "h" * 30)
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, 30)

        # 正则验证
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, "1a2b3c")

        # 业务逻辑验证
        self.failUnlessException(
            InvalidArgumentException, test_rule.validate, 11)

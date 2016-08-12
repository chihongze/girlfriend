# coding: utf-8

"""util.lang模块的测试用例
"""

from girlfriend.testing import GirlFriendTestCase
from girlfriend.util.lang import (
    args2fields,
    SafeOperation
)


class Args2FiledsTestCase(GirlFriendTestCase):

    def test_args2fileds(self):

        class A(object):

            @args2fields()
            def __init__(self, a, b=2, c=5):
                self.d = self._a + self._b + self._c

        a = A(1, 2, 3)
        self.assertEquals(a.d, 6)

        a = A(a=1, b=3)
        self.assertEquals(a.d, 9)

        a = A(1)
        self.assertEquals(a.d, 8)


class SafeOperationTestCase(GirlFriendTestCase):

    def test_safe_operation(self):

        class User(object):

            def __init__(self, name):
                self._name = name

            @property
            def name(self):
                return self._name

            def greeting(self):
                return "Hello, {}".format(self._name)

        user = User("Sam")
        safe_user = SafeOperation(user)
        self.assertEquals(safe_user.name, "Sam")
        self.assertEquals(safe_user.greeting(), "Hello, Sam")

        safe_user = SafeOperation(None)
        self.assertIs(safe_user.name, safe_user)
        self.assertIs(safe_user.greeting(), safe_user)

        # 级联调用
        self.assertIs(safe_user.name.xx.oo, safe_user)
        self.assertIs(safe_user.greeting().hehe().nima().nidaye(), safe_user)

        # 设置值
        safe_user.a = 1
        self.assertIs(safe_user.a, safe_user)

        safe_user = SafeOperation(user)
        safe_user.a = 1
        self.assertEquals(safe_user.a, 1)

        safe_user._name = "Dashuai"
        self.assertEquals(safe_user.name, "Dashuai")
        self.assertEquals(safe_user.greeting(), "Hello, Dashuai")

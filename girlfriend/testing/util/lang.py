# coding: utf-8

"""util.lang模块的测试用例
"""

from girlfriend.testing import GirlFriendTestCase
from girlfriend.util.lang import args2fields


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

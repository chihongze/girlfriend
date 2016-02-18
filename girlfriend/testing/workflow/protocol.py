# coding: utf-8

"""workflow.protocol模块的测试用例
"""

from girlfriend.testing import GirlFriendTestCase
from girlfriend.workflow.protocol import AbstractListener


class AbstractListenerTestCase(GirlFriendTestCase):

    """AbstractListener的测试用例
    """

    def test_wrap_functions(self):

        listener = AbstractListener.wrap_function((
            "on_start", lambda ctx: "on_start",
            "unit_start", lambda ctx: "on_unit_start",
            "unit_finish", lambda ctx: "on_unit_finish",
            "on_finish", lambda ctx: "on_finish",
        ))

        self.assertEquals(listener.on_start(None), "on_start")
        self.assertEquals(listener.on_finish(None), "on_finish")
        self.assertEquals(listener.on_unit_start(None), "on_unit_start")
        self.assertEquals(listener.on_unit_finish(None), "on_unit_finish")

# coding: utf-8

import time
import threading
from girlfriend.testing import GirlFriendTestCase
from girlfriend.workflow.protocol import AbstractSessionCtrl
from girlfriend.workflow.gfworkflow import (
    Job,
    Workflow,
    WorkflowStoppedException,
    SessionCtrl
)


class SessionCtrlTestCase(GirlFriendTestCase):

    def setUp(self):
        pass

    def test_ctrl_stop(self):
        units = (
            Job(
                name="add_one",
                caller=lambda ctx, a: a + 1
            ),
            Job(
                name="sleep",
                caller=lambda ctx: time.sleep(ctx["add_one.result"])
            ),
            Job(
                name="add_two",
                caller=lambda ctx, a: a + 2
            ),
            Job(
                name="add_three",
                caller=lambda ctx, a: a + 3
            )
        )
        wf = Workflow(units)
        ctrl = SessionCtrl()
        event = threading.Event()

        def _exec_wf():
            self.failUnlessException(
                WorkflowStoppedException, Workflow.execute, wf, args={
                    "add_one": (1,),
                    "add_two": ("$add_one.result",),
                    "add_three": ("$add_two.result",)
                }, ctrl=ctrl)
            event.set()
        threading.Thread(target=_exec_wf).start()
        ctrl.stop()
        event.wait()

        # 测试停止在指定的点上
        ctrl = SessionCtrl()
        event = threading.Event()

        def _exec_wf():
            self.failUnlessException(
                WorkflowStoppedException, Workflow.execute, wf, args={
                    "add_one": (1,),
                    "add_two": ("$add_one.result",),
                    "add_three": ("$add_two.result",)
                }, ctrl=ctrl)
            event.set()

        threading.Thread(target=_exec_wf).start()
        ctrl.stop("add_three")
        event.wait()
        self.assertEquals(ctrl.current_unit, "add_three")
        self.assertEquals(ctrl.status, AbstractSessionCtrl.STATUS_STOPPED)

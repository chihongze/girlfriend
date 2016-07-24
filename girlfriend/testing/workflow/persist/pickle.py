# coding: utf-8

from __future__ import absolute_import

import os
import os.path
import pickle
import fixtures
from girlfriend.testing import GirlFriendTestCase
from girlfriend.workflow.gfworkflow import Workflow, Job
from girlfriend.workflow.persist import WorkflowFinishedException
from girlfriend.workflow.persist.file import (
    STATUS_RUNNING,
    STATUS_FINISHED
)
from girlfriend.workflow.persist.pickle import (
    PickleRecoverPolicy,
    PicklePersistListener,
)


class WorkflowFixture(fixtures.Fixture):

    def __init__(self, dump_to):
        self._dump_to = dump_to

    def setUp(self):
        wf = Workflow([
            Job(
                name="add",
                caller=lambda ctx, x, y: x + y
            ),
            Job(
                name="divide",
                caller=lambda ctx, x, y: x / y
            )
        ])
        wf.add_listener(PicklePersistListener(self._dump_to))
        self.wf = wf

    def cleanUp(self):
        if os.path.exists(self._dump_to):
            os.remove(self._dump_to)


class PicklePersistListenerTestCase(GirlFriendTestCase):

    def testDump(self):
        # 正常结束
        fixture = WorkflowFixture("dump.dat")
        self.useFixture(fixture)
        rs = fixture.wf.execute({
            "add": [3, 5],
            "divide": ["$add.result", 2]
        })
        self.assertEquals(rs.result, 4)
        ctx = pickle.load(open("dump.dat", "r"))
        status = ctx["status"]
        self.assertEquals(status, STATUS_FINISHED)
        data = ctx["data"]
        self.assertEquals(data["divide.result"], 4)

    def testDumpWithError(self):
        # 中间遇到了异常
        fixture = WorkflowFixture("dump.dat")
        self.useFixture(fixture)
        fixture.wf.execute({
            "add": [3, 5],
            "divide": ["$add.result", 0]
        })
        ctx = pickle.load(open("dump.dat", "r"))
        status = ctx["status"]
        self.assertEquals(status, STATUS_RUNNING)
        data = ctx["data"]
        self.assertEquals(data["add.result"], 8)


class PickleRecoverPolicyTestCase(GirlFriendTestCase):

    def testLoad(self):
        fixture = WorkflowFixture("dump.dat")
        self.useFixture(fixture)
        fixture.wf.execute({
            "add": [3, 5],
            "divide": ["$add.result", 2]
        })

        # 已经处于完成状态
        prp = PickleRecoverPolicy("dump.dat")
        try:
            prp.load()
            self.fail(u"工作流已经完成，应该抛出NoNeedRecoverException")
        except WorkflowFinishedException as e:
            print e.message

    def testLoadWithCrash(self):
        fixture = WorkflowFixture("dump.dat")
        self.useFixture(fixture)
        fixture.wf.execute({
            "add": [3, 5],
            "divide": ["$add.result", 0]
        })

        prp = PickleRecoverPolicy("dump.dat")
        recover_info = prp.load()
        self.assertEquals(recover_info.begin_unit, "divide")
        ctx = recover_info.context_factory()
        self.assertEquals(ctx["add.result"], 8)

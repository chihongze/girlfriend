# coding: utf-8

from __future__ import absolute_import

import time
from concurrent.futures import ThreadPoolExecutor
from girlfriend.testing import GirlFriendTestCase
from girlfriend.workflow.gfworkflow import Job
from girlfriend.workflow.concurrent import (
    ConcurrentJob,
    ConcurrentForeachJob,
    BufferingJob
)


class ConcurrentJobTestCase(GirlFriendTestCase):

    def setUp(self):

        def task(context, number):
            print "begin task {} ...".format(number)
            time.sleep(number)
            print "finish task {}".format(number)
            return number

        self.sub_jobs = (
            Job(
                name="job_1",
                caller=task,
                args=[2],
            ),
            Job(
                name="job_2",
                caller=task,
                args=[3]
            ),
            Job(
                name="job_3",
                caller=task,
                args=[5]
            ),
        )

    def test_execute_with_thread_pool(self):
        self._test_execute(ThreadPoolExecutor)

    def _test_execute(self, pool_type):
        concurrent_job = ConcurrentJob(
            name="con_job",
            sub_jobs=self.sub_jobs,
            pool_type=pool_type
        )
        context = self.workflow_context()
        begin_time = time.time()
        result = concurrent_job.execute(context)
        print "used_time:", (time.time() - begin_time)
        self.assertEquals(result, [2, 3, 5])
        self.assertEquals(context["con_job.result"], [2, 3, 5])

        # with join
        concurrent_job = ConcurrentJob(
            name="con_job",
            sub_jobs=self.sub_jobs,
            join=lambda ctx, result: sum(result),
            pool_type=pool_type
        )
        result = concurrent_job.execute(context)
        self.assertEquals(result, 10)
        self.assertEquals(context["con_job.result"], 10)

        # with exisiting pool
        begin_time = time.time()
        ConcurrentJob(
            name="con_job",
            sub_jobs=self.sub_jobs,
            pool=pool_type(max_workers=2)
        ).execute(context)
        print "used time with fixed pool(size=2):", (time.time() - begin_time)

        # with error_happed
        sub_jobs = self.sub_jobs + (Job(
            name="error_job",
            caller=lambda ctx: 1 / 0
        ),)
        error_job = ConcurrentJob(
            name="con_job",
            sub_jobs=sub_jobs,
            pool_type=pool_type,
            error_action="stop"
        )
        self.failUnlessException(ZeroDivisionError, error_job.execute, context)

        def excetion_handler(context, exc_t, exc_v, tb):
            print "Caught exception: {}".format(exc_t.__name__)

        result = ConcurrentJob(
            name="con_job",
            sub_jobs=sub_jobs,
            pool_type=pool_type,
            error_action="continue",
            error_handler=excetion_handler,
            error_default_value=-1
        ).execute(context)
        self.assertEquals(result, [2, 3, 5, -1])


def task(context, number):
    print "begin task {} ...".format(number)
    time.sleep(number)
    print "finish task {}".format(number)
    return number


class ConcurrentForeachJobTestCase(GirlFriendTestCase):

    def test_concurrent_foreach(self):
        job = ConcurrentForeachJob(
            name="test",
            caller=task,
            args=[[5]] * 20
        )

        context = self.workflow_context()
        result = job.execute(context)
        self.assertEquals([5] * 20, result)
        self.assertEquals([5] * 20, context["test.result"])

        # with sub_join
        job = ConcurrentForeachJob(
            name="test",
            caller=task,
            args=[[5]] * 20,
            sub_join=lambda ctx, result: sum(result)
        )
        result = job.execute(context)
        self.assertEquals(result, [10] * 10)
        self.assertEquals(context["test.result"], [10] * 10)

        # with result join
        job = ConcurrentForeachJob(
            name="test",
            caller=task,
            args=[[5]] * 20,
            sub_join=lambda ctx, result: sum(result),
            result_join=lambda ctx, result: sum(result)
        )
        result = job.execute(context)
        self.assertEquals(result, 100)
        self.assertEquals(context["test.result"], 100)

        # with generator args
        def gen_args():
            for _ in xrange(0, 20):
                yield [5]

        job = ConcurrentForeachJob(
            name="test",
            caller=task,
            args=gen_args,
            task_num_per_thread=3,
        )
        result = job.execute(context)
        self.assertEquals([5] * 20, result)
        self.assertEquals([5] * 20, context["test.result"])


class BufferingJobTestCase(GirlFriendTestCase):

    def test_execute(self):
        job = BufferingJob(
            "test",
            caller=task,
            args=[2],
            max_items=5,
        )
        context = self.workflow_context()
        result = job.execute(context)
        self.assertEquals(result, [2] * 5)

        # timeout and not immediately
        job = BufferingJob(
            "test",
            caller=task,
            args=[3],
            max_items=5,
            timeout=1
        )
        result = job.execute(context)
        self.assertEquals(result, [3])

        # timeout and immedialely
        job = BufferingJob(
            "test",
            caller=task,
            args=[3],
            timeout=1,
            immediately=True
        )
        result = job.execute(context)
        self.assertEquals(result, [])

        # give_back_handler
        def give_back_handler(context, un_handle_elements):
            print "unhandled elements:", un_handle_elements

        job = BufferingJob(
            "test",
            caller=task,
            args=[3],
            timeout=1,
            immediately=True,
            max_items=1,
            give_back_handler=give_back_handler
        )
        result = job.execute(context)
        self.assertEquals(result, [])

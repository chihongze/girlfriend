# coding: utf-8

from __future__ import absolute_import

import time
import threading
from girlfriend.testing import GirlFriendTestCase
from girlfriend.util.concurrent import CountDownLatch, CyclicBarrier


class CountDownLatchTestCase(GirlFriendTestCase):

    def test_count_down_latch(self):
        latch = CountDownLatch(10)

        def foo(number):
            print "begin task: ", number
            time.sleep(1)
            print "end task: ", number
            latch.count_down()

        for n in xrange(0, 10):
            threading.Thread(target=foo, args=(n,)).start()

        latch.await()


class CyclicBarrierTestCase(GirlFriendTestCase):

    def test_cyclic_barrier(self):
        barrier = CyclicBarrier(3)

        def foo(number):
            for _ in xrange(0, 3):
                print "task: ", number
                time.sleep(number)
                barrier.await()

        for n in xrange(1, 4):
            threading.Thread(target=foo, args=(n,)).start()

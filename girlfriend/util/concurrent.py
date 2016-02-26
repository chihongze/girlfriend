# coding: utf-8

"""并发工具集
"""

from __future__ import absolute_import

import threading
from girlfriend.exception import InvalidArgumentException


class CountDownLatch(object):

    """基于计数的闭锁实现
    """

    def __init__(self, count):
        if count <= 0:
            raise InvalidArgumentException(u"count参数必须为正整数")
        self._count = count
        self._condition = threading.Condition()

    def count_down(self):
        with self._condition:
            self._count -= 1
            if self._count <= 0:
                self._condition.notifyAll()

    def await(self):
        with self._condition:
            while self._count > 0:
                self._condition.wait()


class CyclicBarrier(object):

    """循环关卡实现
    """

    def __init__(self, count):
        if count <= 0:
            raise InvalidArgumentException(u"count参数必须为正整数")
        self._count = count
        self._awaiting_count = count
        self._condition = threading.Condition()

    def await(self):
        with self._condition:
            self._awaiting_count -= 1
            if self._awaiting_count <= 0:
                self._awaiting_count = self._count  # 回收再利用
                self._condition.notifyAll()
            else:
                self._condition.wait()

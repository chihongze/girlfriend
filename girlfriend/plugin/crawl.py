# coding: utf-8

import sys
import types
import gevent
import requests
from gevent.queue import Queue, Empty
from gevent.pool import Pool as GeventPool
from girlfriend.exception import InvalidArgumentException


def _default_parser(context, response, queue):
    """默认的Response对象解析器
    """
    content_type = response.headers["content-type"]
    if content_type.startswith("application/json"):
        return response.json()
    else:
        return response.text


class CrawlPlugin(object):

    """基于gevent和requests模块的简单爬虫插件
    """

    name = "crawl"

    def execute(self, context, start_req, parser=_default_parser,
                pool=None, pool_size=None):
        """
        :param context: 上下文对象
        :param start_req: 起始请求列表
        :param parser: Response对象解析器
        :param concurrent: 是否采用并发方式抓取
        :param pool: 指定已有的gevent pool
        """

        if pool or pool_size:
            # 并发请求
            return self._concurrent_execute(
                context, start_req, parser,
                pool, pool_size)
        else:
            # 同步请求
            return self._sync_execute(context, start_req, parser)

    def _sync_execute(self, context, start_req, parser):
        queue = list(start_req)
        result = []
        while queue:
            req = queue.pop(0)
            req = self._check_req(req)
            if req.parser is None:
                req.parser = parser
            result.append(req(context, queue))
        return result

    def _concurrent_execute(self, context, start_req, parser, pool, pool_size):
        queue = Queue()  # 任务队列

        # 将初始化请求加入任务队列
        for r in start_req:
            queue.put_nowait(r)

        if pool is None:
            pool = GeventPool(pool_size)

        greenlets = []

        while True:
            try:
                req = self._check_req(queue.get(timeout=1))
                if req.parser is None:
                    req.parser = parser
                greenlets.append(pool.spawn(req, context, queue))
            except Empty:
                break

        return [greenlet.get() for greenlet in greenlets]

    def _check_req(self, req):
        if not isinstance(req, Req):
            if isinstance(req, types.StringTypes):
                req = Req("get", req)
            else:
                raise InvalidArgumentException(u"req_list参数中包含不合法的类型")
        return req


class Req(object):

    """该对象用于描述HTTP请求
    """

    methods = {
        "get": requests.get,
        "post": requests.post,
        "put": requests.put,
        "delete": requests.delete,
        "options": requests.options,
        "head": requests.head
    }

    def __init__(self, method, *args, **kws):
        """
        :param method: HTTP请求方法
        :param parser: 响应解析器
        :param *args: requests参数
        :param **kws: requests参数
        """
        self.method = Req.methods[method.lower()]
        self.args = args
        self.sleep = kws.pop("sleep", None)
        self.parser = kws.pop("parser", None)
        self.kws = kws

    def __call__(self, context, queue):
        """
        :param context: 上下文
        :param queue: 抓取队列
        """
        try:
            response = self.method(*self.args, **self.kws)
            result = self.parser(context, response, queue)
            if self.sleep:
                gevent.sleep(self.sleep)
            return result
        except:
            context.logger.exception(u"crawl error")
            return sys.exc_info()

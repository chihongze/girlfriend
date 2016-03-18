# coding: utf-8
import ujson
import fixtures
import httpretty
from girlfriend.testing import GirlFriendTestCase
from girlfriend.plugin.crawl import (
    Req,
    CrawlPlugin,
    _default_parser
)
from gevent import monkey
monkey.patch_all()

sam_profile = {"id": 1, "name": "Sam", "blog": "http://test.gf/blog/sam"}
jack_profile = {"id": 2, "name": "Jack", "blog": "http://test.gf/blog/jack"}

sams_articles = [
    {"id": 1, "title": "About Hadoop Streaming"},
    {"id": 2, "title": "Learning Scala the hard way"}
]

jacks_articles = [
    {"id": 1, "title": "JVM Tunning"},
    {"id": 2, "title": "HTML5 Security"}
]


class HttpServerFixture(fixtures.Fixture):

    def setUp(self):
        httpretty.enable()
        httpretty.register_uri(
            httpretty.GET, "http://test.gf/users",
            body=ujson.dumps([
                sam_profile,
                jack_profile,
            ]),
            content_type="application/json"
        )
        httpretty.register_uri(
            httpretty.GET, "http://test.gf/blog/sam",
            body=ujson.dumps(sams_articles),
            content_type="application/json"
        )
        httpretty.register_uri(
            httpretty.GET, "http://test.gf/blog/jack",
            body=ujson.dumps(jacks_articles),
            content_type="application/json"
        )

    def cleanUp(self):
        httpretty.disable()
        httpretty.reset()


class ReqTestCase(GirlFriendTestCase):

    def test_req(self):
        http_server_fixture = HttpServerFixture()
        self.useFixture(http_server_fixture)
        context = self.workflow_context()
        result = Req(
            "GET",
            "http://test.gf/users",
            parser=_default_parser
        )(context, [])
        self.assertEquals(result, [sam_profile, jack_profile])


class CrawlPluginTestCase(GirlFriendTestCase):

    def test_non_concurrent_crawl(self):

        self.useFixture(HttpServerFixture())

        # 非并发情形下的抓取
        def parser(context, response, queue):
            json_content = response.json()
            if response.url == "http://test.gf/users":
                for profile in response.json():
                    queue.append(profile["blog"])
                return json_content
            elif response.url.startswith("http://test.gf/blog"):
                return json_content
            else:
                raise "Unknown url: " + response.url

        context = self.workflow_context()
        crawl_plugin = CrawlPlugin()
        rs = crawl_plugin.execute(
            context,
            ["http://test.gf/users"],
            parser=parser
        )
        self.assertEquals(
            rs,
            [[sam_profile, jack_profile], sams_articles, jacks_articles]
        )

    def test_concurrent_crawl(self):
        def parser(context, response, queue):
            pass
        context = self.workflow_context()
        crawl_plugin = CrawlPlugin()
        rs = crawl_plugin.execute(
            context, ["https://api.douban.com/v2/book/3259440"] * 100,
            pool_size=100)
        self.assertEquals(
            [u"[日] 东野圭吾"] * 100, [book_info["author"][0] for book_info in rs])

# coding: utf-8

"""json plugin testcase
"""

import os
import ujson
import httpretty

from girlfriend.testing import GirlFriendTestCase
from girlfriend.data.table import (
    TableWrapper,
    Title
)
from girlfriend.plugin.json import JSONR, JSONW

JSON_LINE_CONTENT = """
{"id": 1, "name": "Sam", "grade": "A"}
{"id": 2, "name": "Tom", "grade": "B"}
{"id": 3, "name": "Betty", "grade": "A"}
"""

JSON_ARRAY_CONTENT = """
[
  {"id": 1, "name": "Jack", "grade": "A"},
  {"id": 2, "name": "Peter", "grade": "B"},
  {"id": 3, "name": "James", "grade": "A"}
]
"""

JSON_OBJECT_CONTENT = """
{
  "code": 200,
  "value": {
    "users": [
      {"id": 1, "name": "Sam", "grade": "A"},
      {"id": 2, "name": "Jack", "grade": "A"},
      {"id": 3, "name": "James", "grade": "A"}
    ]
  }
}
"""

JSON_BLOCK_CONTENT = """
hhhhhhhhsdddsddwwdsdd
{
    "name": "Sam",
    "scores": {
        "A": 102,
        "B": 110,
        "C": 115
    }
}sssssssss{
    "name": "Jack",
    "scores": {
        "A": 110,
        "B": 50,
        "C": 60,
        "D": "{-_-}"
    }
}
"""


class Student(object):

    def __init__(self, id, name, grade):
        self.id = id
        self.name = name
        self.grade = grade


class JSONReaderPluginTestCase(GirlFriendTestCase):

    def setUp(self):
        with open("line_file.json", "w") as f:
            f.write(JSON_LINE_CONTENT)
        with open("array_file.json", "w") as f:
            f.write(JSON_ARRAY_CONTENT)
        with open("object_file.json", "w") as f:
            f.write(JSON_OBJECT_CONTENT)
        with open("block_file.json", "w") as f:
            f.write(JSON_BLOCK_CONTENT)

        httpretty.enable()

        httpretty.register_uri(
            httpretty.GET,
            "http://test.gf/line",
            body=JSON_LINE_CONTENT,
            content_type="text/plain"
        )

        httpretty.register_uri(
            httpretty.GET,
            "http://test.gf/array",
            body=JSON_ARRAY_CONTENT,
            content_type="application/json"
        )

        httpretty.register_uri(
            httpretty.GET,
            "http://test.gf/object",
            body=JSON_OBJECT_CONTENT,
            content_type="application/json"
        )

    def test_read_line_with_file(self):
        ctx = {}

        # 测试一般执行
        result = JSONR("line_file.json", "line")(ctx)
        self.assertEquals(len(result), 3)
        self.assertEquals(result[0], {"id": 1, "name": "Sam", "grade": "A"})

        # 测试record_handler
        JSONR("line_file.json", "line",
              record_handler=lambda row: {row.pop("name"): row},
              variable="test")(ctx)
        test_result = ctx["test"]
        self.assertEquals(test_result[0], {"Sam": {"id": 1, "grade": "A"}})

        # 测试result_wrapper
        table = JSONR("line_file.json", "line",
                      result_wrapper=TableWrapper("students", (
                          Title("id", u"编号"),
                          Title("name", u"姓名"),
                          Title("grade", u"等级")
                      )))(ctx)
        print "\n", table
        row_0 = table[0]
        self.assertEquals(
            (row_0.id, row_0.name, row_0.grade),
            (1, "Sam", "A")
        )

    def test_read_line_with_web(self):
        ctx = {}

        # 测试一般执行
        result = JSONR("http://test.gf/line", "line")(ctx)
        self.assertEquals(len(result), 3)
        self.assertEquals(result[0], {"id": 1, "name": "Sam", "grade": "A"})

    def test_read_json_array(self):
        ctx = {}

        # 测试一般执行
        result = JSONR("array_file.json", "array")(ctx)
        self.assertEquals(len(result), 3)
        self.assertEquals(result[0], {"id": 1, "name": "Jack", "grade": "A"})

        # URL加载执行
        result = JSONR("http://test.gf/array", "array")(ctx)
        self.assertEquals(len(result), 3)
        self.assertEquals(result[0], {"id": 1, "name": "Jack", "grade": "A"})

        # 测试record_handler
        result = JSONR("http://test.gf/array", "array",
                       record_handler=lambda r: Student(**r))(ctx)
        std = result[0]
        self.assertEquals((std.id, std.name, std.grade), (1, "Jack", "A"))

        table = JSONR("http://test.gf/array", "array",
                      record_handler=lambda r: Student(**r),
                      result_wrapper=TableWrapper(
                          "student",
                          (Title("id"), Title("name"), Title("grade"))))(ctx)
        print "\n", table
        row_0 = table[0]
        self.assertEquals(
            (row_0.id, row_0.name, row_0.grade),
            (1, "Jack", "A")
        )

    def test_read_json_object(self):
        ctx = {}

        # 测试从文件提取
        result = JSONR("object_file.json", "extract:value.users")(ctx)
        self.assertEquals(len(result), 3)
        self.assertEquals(result[0], {"id": 1, "name": "Sam", "grade": "A"})

        # 测试从web提取
        result = JSONR("http://test.gf/object", "extract:value.users")(ctx)
        self.assertEquals(len(result), 3)
        self.assertEquals(result[0], {"id": 1, "name": "Sam", "grade": "A"})

        # 测试record_handler
        result = JSONR("http://test.gf/object", "extract:value.users",
                       record_handler=lambda r: Student(**r))(ctx)
        self.assertEquals(len(result), 3)
        std = result[0]
        self.assertEquals((std.id, std.name, std.grade), (1, "Sam", "A"))

        # 测试result_wrapper
        table = JSONR("http://test.gf/object", "extract:value.users",
                      record_handler=lambda r: Student(**r))(ctx)
        self.assertEquals(len(result), 3)
        row_0 = table[0]
        self.assertEquals(
            (row_0.id, row_0.name, row_0.grade),
            (1, "Sam", "A")
        )

    def test_read_json_blocks(self):
        ctx = {}

        result = JSONR("block_file.json", "block")(ctx)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0], {"name": "Sam",
                                      "scores": {
                                          "A": 102,
                                          "B": 110,
                                          "C": 115
                                      }})

    def tearDown(self):
        os.remove("line_file.json")
        os.remove("array_file.json")
        os.remove("object_file.json")
        os.remove("block_file.json")
        httpretty.disable()
        httpretty.reset()


class JSONWriterPluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.records = [
            {"id": 1, "name": "Sam", "gender": 1},
            {"id": 2, "name": "Jack", "gender": 1},
            {"id": 3, "name": "Betty", "gender": 0},
        ]
        httpretty.enable()

    def test_write_json_file_by_line(self):
        JSONW("line_file.json", "line", self.records)({})
        with open("line_file.json", "r") as f:
            for idx, line in enumerate(f):
                json_obj = ujson.loads(line.strip())
                self.assertEquals(json_obj, self.records[idx])
        os.remove("line_file.json")

    def test_write_object(self):
        JSONW("object_file.json", "object", self.records[0])({})
        with open("object_file.json", "r") as f:
            self.assertEquals(ujson.loads(f.read()), self.records[0])
        os.remove("object_file.json")

    def test_write_array(self):
        JSONW("array_file.json", "array", self.records)({})
        with open("array_file.json", "r") as f:
            self.assertEquals(ujson.loads(f.read()), self.records)
        os.remove("array_file.json")

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

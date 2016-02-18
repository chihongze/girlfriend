# coding: utf-8

import os
import httpretty
from girlfriend.testing import GirlFriendTestCase
from girlfriend.plugin.csv import CSVR, CSVW


STUDENTS = (
    ("1", "Sam", "1"),
    ("2", "Jack", "2"),
    ("3", "James", "2"),
    ("4", "Lucy", "2"),
    ("5", "Peter", "1")
)

CSV_CONTENT = "\n".join(",".join(row) for row in STUDENTS)


class CSVReaderTestCase(GirlFriendTestCase):

    def setUp(self):
        with open("test.csv", "w") as f:
            f.write(CSV_CONTENT)

        httpretty.enable()

        httpretty.register_uri(
            httpretty.GET,
            "http://test.gf/csv",
            body=CSV_CONTENT,
            content_type="text/plain"
        )

    def test_read_from_file(self):
        result = CSVR(
            "test.csv", record_handler=tuple, result_wrapper=tuple)({})
        self.assertEquals(result, STUDENTS)
        result = CSVR(
            content=CSV_CONTENT, record_handler=tuple,
            result_wrapper=tuple)({})
        self.assertEquals(result, STUDENTS)

    def test_read_from_web(self):
        result = CSVR(
            "http://test.gf/csv",
            record_handler=tuple, result_wrapper=tuple)({})
        self.assertEquals(result, STUDENTS)

    def tearDown(self):
        os.remove("test.csv")
        httpretty.disable()
        httpretty.reset()


class Student(object):

    def __init__(self, id_, name, grade):
        self.id = id_
        self.name = name
        self.grade = grade

student_objects = (
    Student(1, "Sam", 1),
    Student(2, "Jack", 1),
    Student(3, "Tom", 2),
    Student(4, "Lucy", 2),
    Student(5, "James", 2)
)


class CSVWriterPluginTestCase(GirlFriendTestCase):

    def setUp(self):
        pass

    def test_write_file(self):
        CSVW(
            "test.csv", student_objects,
            record_handler=lambda std: (std.id, std.name, std.grade)
        )({})
        with open("test.csv", "r") as f:
            print "\n", f.read()
        os.remove("test.csv")

    def test_write_context_var(self):
        ctx = {}
        CSVW(
            "memory:test_csv", student_objects,
            record_handler=lambda std: (std.id, std.name, std.grade)
        )(ctx)
        print "\n", ctx["test_csv"].buf

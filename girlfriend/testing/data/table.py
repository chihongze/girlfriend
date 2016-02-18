# coding: utf-8

from girlfriend.testing import GirlFriendTestCase
from girlfriend.data.table import (
    Title,
    ListTable,
    ObjectTable,
    DictTable
)
from girlfriend.data.exception import InvalidSizeException


class ListTableTestCase(GirlFriendTestCase):

    def setUp(self):
        titles = (
            Title("id"),
            Title("name"),
            Title("age"),
            Title("grade"),
        )
        self.table = ListTable("test_table", titles)

        self.data = [
            (1, "Sam", 26, "A"),
            (2, "Jack", 31, "B"),
            (3, "James", 32, "C")
        ]

        self.wrapped_table = ListTable("test_table", titles, self.data)

    def test_append(self):
        """测试append方法
        """
        self.table.append([1, "SamChi", 26, "A"])
        self.assertEquals(
            (
                self.table[0].id,
                self.table[0].name,
                self.table[0].age,
                self.table[0].grade
            ),
            (1, "SamChi", 26, "A")
        )

        self.failUnlessException(
            InvalidSizeException,
            ListTable.append,
            self.table,
            [2, "James", 31, "X", 0])

        self.wrapped_table.append((4, "Betty", 21, "A"))
        self.assertEquals((4, "Betty", 21, "A"), self.data[-1])
        # test multi get
        self.assertEquals(
            self.wrapped_table[-1]["id", "name", "age", "grade"],
            (4, "Betty", 21, "A")
        )

    def test_iter(self):
        """测试迭代器
        """
        data = [
            (1, "Sam", 26, "A"),
            (2, "Jack", 31, "B"),
            (3, "James", 32, "C")
        ]

        for rowlist in data:
            self.table.append(rowlist)

        for idx, row in enumerate(self.table):
            self.assertEquals(
                (row.id, row.name, row.age, row.grade), data[idx])


class Student(object):

    def __init__(self, id, name, grade):
        self.id = id
        self.name = name
        self.grade = grade


class ObjectTableTestCase(GirlFriendTestCase):

    def setUp(self):
        titles = (
            Title("id", u"编号"),
            Title("name", u"姓名"),
            Title("grade", u"年级")
        )

        self.table = ObjectTable("student_table", titles)

        students = (
            Student(1, "Sam", 1),
            Student(2, "Jack", 1),
            Student(3, "Peter", 2)
        )

        self.students = students

        self.wrapped_table = ObjectTable("student_table", titles, students)

    def test_append(self):
        self.table.append(Student(4, "James", 2))
        self.assertEquals(self.table[-1].id, 4)
        self.assertEquals(self.table[0][1], "James")
        self.assertEquals(self.table[0]["grade"], 2)

    def test_iter(self):
        for idx, row in enumerate(self.wrapped_table):
            std = self.students[idx]
            self.assertEquals(
                row["id", "name", "grade"],
                (std.id, std.name, std.grade)
            )


class DictTableTestCase(GirlFriendTestCase):

    def setUp(self):
        titles = (
            Title("id", u"编号"),
            Title("name", u"姓名"),
            Title("grade", u"年级")
        )

        self.table = DictTable("student_table", titles)

        students = (
            {"id": 1, "name": "Sam", "grade": 1},
            {"id": 2, "name": "Jack", "grade": 1},
            {"id": 3, "name": "Peter", "grade": 2}
        )

        self.students = students
        self.wrapped_table = DictTable("student_table", titles, students)

    def test_append(self):
        self.table.append({"id": 4, "name": "James", "grade": 2})
        self.assertEquals(self.table[-1].id, 4)
        self.assertEquals(self.table[0][1], "James")
        self.assertEquals(self.table[0]["grade"], 2)

    def test_iter(self):
        for idx, row in enumerate(self.wrapped_table):
            record = self.students[idx]
            self.assertEquals(
                row["id", "name", "grade"],
                tuple(record[k] for k in ("id", "name", "grade"))
            )

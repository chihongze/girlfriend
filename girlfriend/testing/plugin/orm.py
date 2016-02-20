# coding: utf-8

import os
import os.path
import sqlite3
from girlfriend.plugin.orm import (
    EngineManager,
    _engine_manager,
    Query,
    SQL,
    KeyExtractWrapper
)
from girlfriend.util.config import Config
from girlfriend.exception import (
    InvalidArgumentException,
    InvalidStatusException
)
from girlfriend.testing import GirlFriendTestCase
from sqlalchemy import (
    Column,
    Integer,
    String,
    func,
    and_
)
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.declarative import declarative_base
from girlfriend.plugin import plugin_manager
from girlfriend.data.table import TableWrapper, Title


class EngineManagerTestCase(GirlFriendTestCase):

    def setUp(self):
        self.test_db_file = "/tmp/gftest.db"
        connection_url = "sqlite:///{}".format(self.test_db_file)
        self.config = Config({
            "db_test": {
                "connect_url": "sqlite:///:memory:",
                "pool_policy": "test"
            },
            "db_test2": {
                "connect_url": connection_url
            },
            "dbpool_test": {
                "poolclass": "QueuePool",
                "pool_size": 10,
                "pool_recycle": 3600,
                "pool_timeout": 20
            }
        })
        conn = sqlite3.connect(self.test_db_file)
        create_table_sql = """
        create table user (
            id integer primary key,
            name varchar(10) unique,
            grade int not null,
            description text not null
        )
        """
        conn.execute(create_table_sql)
        conn.execute((
            "insert into user (id, name, grade, description) values "
            "(1, 'SamChi', 1, 'I am SamChi')"
        ))
        conn.commit()

    def tearDown(self):
        if os.path.exists(self.test_db_file):
            os.remove(self.test_db_file)

    def test_validate(self):
        engine_manager = EngineManager()
        engine_manager.validate_config(self.config)

        # 是否已经设置默认参数
        self.assertEquals(self.config["db_test"]["connect_args"], "{}")
        self.assertEquals(self.config["db_test"]["encoding"], "utf-8")

        bad_config = Config({
            "db_test": {
                "connect_url": "hehe"  # url format error
            }
        })

        # 因为已经验证过配置了，所以同一个manager对象不会进行重复验证
        engine_manager.validate_config(bad_config)  # No Exception happened

        engine_manager = EngineManager()
        self.failUnlessException(
            InvalidArgumentException,
            engine_manager.validate_config, bad_config)

        bad_config["db_test"]["connect_url"] = "sqlite:///:memory:"
        bad_config["db_test"]["connect_args"] = "{h"
        engine_manager = EngineManager()
        self.failUnlessException(
            InvalidArgumentException,
            engine_manager.validate_config, bad_config)

    def test_init_all(self):
        engine_manager = EngineManager()
        # 同一个manager对象，重复初始化不会发生任何问题
        for i in xrange(0, 100):
            engine_manager.validate_config(self.config)
            engine_manager.init_all(self.config)

            test_engine = engine_manager.engine("test")
            self.assertIsNotNone(test_engine)

            # 连接池相关参数
            pool = test_engine.engine.pool
            self.assertIsInstance(pool, QueuePool)
            self.assertEquals(pool.size(), 10)
            self.assertEquals(pool._recycle, 3600)
            self.assertEquals(pool._timeout, 20)

            # 测试可否连接
            connection = test_engine.engine.connect()
            result = connection.execute("select 1 + 1")
            self.assertEquals(tuple(result)[0][0], 2)

            test_engine2 = engine_manager.engine("test2")
            self.assertIsNotNone(test_engine2)

            connection = test_engine2.engine.connect()
            result = connection.execute("select * from user")
            self.assertEquals(tuple(result)[0],
                              (1, "SamChi", 1, "I am SamChi"))

    def test_dispose_all(self):
        engine_manager = EngineManager()
        engine_manager.validate_config(self.config)
        engine_manager.init_all(self.config)
        engine_manager.dispose_all()

        self.failUnlessException(InvalidStatusException,
                                 engine_manager.engine, "test")

Base = declarative_base()


class Student(Base):

    __tablename__ = "student"

    id = Column(Integer, primary_key=True)

    name = Column(String(10))

    fullname = Column(String(20))

    grade = Column(Integer)


class Grade(Base):

    __tablename__ = "grade"

    id = Column(Integer, primary_key=True)

    name = Column(String(10))


class QueryTestCase(GirlFriendTestCase):

    def setUp(self):
        config = Config({
            "db_test": {
                "connect_url": "sqlite:///:memory:",
                "pool_policy": "test"
            },
            "dbpool_test": {
                "poolclass": "QueuePool",
                "pool_size": 10,
            }
        })
        _engine_manager.validate_config(config)
        _engine_manager.init_all(config)
        global Base
        engine_container = _engine_manager.engine("test")
        Base.metadata.create_all(engine_container.engine)

        student_sam = Student(id=1, name="Sam", fullname="SamChi", grade=1)
        student_jack = Student(id=2, name="Jack", fullname="JackMa", grade=2)
        student_betty = Student(
            id=3, name="Betty", fullname="Betty Smith", grade=1)
        grade1 = Grade(id=1, name="Grade One")
        grade2 = Grade(id=2, name="Grade Two")

        session = engine_container.session()
        session.add_all([
            student_sam,
            student_jack,
            student_betty,
            grade1,
            grade2
        ])
        session.commit()
        self.config = config

    def test_query(self):
        ctx = {}

        # 执行纯SQL语句的情景
        q = Query(
            "test", "test_result", Student,
            "select * from student order by id")
        q(ctx)
        self._check_students_list(ctx["test_result"])

        # 进行auto map的情况
        q = Query("test", "test_result", "student",
                  "select * from student order by id")
        q(ctx)
        self._check_students_list(ctx["test_result"])

        # 多个映射类的情况
        q = Query("test", "test_result",
                  (Student.id, Student.name, Grade.name),
                  ("select s.id, s.name, g.name from student s, grade g "
                   "where s.grade = g.id order by s.id"))
        q(ctx)
        self.assertTrue(ctx["test_result"][0], (1, "Sam", "Grade One"))

        # auto map field 的情况
        q = Query(
            "test", "test_result",
            (Student.id, "student.name", "grade.name"),
            ("select s.id, s.name, g.name from student s, grade g "
             "where s.grade = g.id order by s.id"))
        q(ctx)
        self.assertTrue(ctx["test_result"][0], (1, "Sam", "Grade One"))

        # 查询字符串表达式
        q = Query("test", "test_result", Student,
                  "id > :id and name = :name",
                  params={"id": 1, "name": "Betty"})
        q(ctx)
        students = ctx["test_result"]
        self.assertEquals(len(students), 1)
        s = students[0]
        self.assertEquals((s.id, s.name, s.grade), (3, "Betty", 1))

        # order by
        q = Query("test", "test_result", Student,
                  "id > :id", order_by="id desc", params={"id": 1})
        q(ctx)
        self.assertEquals([std.id for std in ctx["test_result"]], [3, 2])

        # group by and count
        q = Query("test", "test_result",
                  ("student.grade", func.count('*')), order_by="grade desc",
                  group_by="student.grade")
        q(ctx)
        grade_counts = ctx["test_result"]
        self.assertEquals(len(grade_counts), 2)
        self.assertEquals(grade_counts[0], (2, 1))

        # 条件查询
        q = Query("test", "test_result", Student, and_(
            Student.grade == 1, Student.name == "Betty"))
        q(ctx)
        records = ctx["test_result"]
        self.assertEquals(len(records), 1)

        # 通过自定义函数来构建查询条件
        def my_query(session, ctx, student, grade):
            query = session.query(student.id, grade.name).filter(
                student.grade == grade.id)
            return query.all()

        #  只返回查询对象
        q_a = Query("test", "test_result", ("student", "grade"),
                    lambda s, ctx, std, grade:
                    s.query(std.id, grade.name).filter(std.grade == grade.id))
        #  通过all()返回查询结果
        q_b = Query("test", "test_result", ("student", "grade"),
                    lambda s, ctx, std, grade:
                    s.query(std.id, grade.name).filter(
                        std.grade == grade.id).all())
        for q in (q_a, q_b):
            q(ctx)
            records = ctx["test_result"]
            self.assertEquals(len(records), 3)
            self.assertEquals(records[0], (1, "Grade One"))

        class StudentGrade(object):

            def __init__(self, row):
                student, grade = row
                self.id = student.id
                self.name = student.name
                self.grade = grade.name

        # row_handler
        q = Query("test", "test_result", (Student, Grade),
                  Student.grade == Grade.id, row_handler=StudentGrade,
                  order_by=Student.id)
        q(ctx)
        records = ctx["test_result"]
        self.assertEquals(len(records), 3)
        self.assertEquals(
            (records[0].id, records[0].name, records[0].grade),
            (1, "Sam", "Grade One")
        )

        # Table Wrapper
        q = Query(
            "test", "test_table",
            (Student.id, Student.name, Student.grade),
            result_wrapper=TableWrapper(
                "student",
                (
                    Title("id", u"编号"),
                    Title("name", u"姓名"),
                    Title("grade", u"年级")
                ))
        )
        q(ctx)
        test_table = ctx["test_table"]
        self.assertEquals(test_table.cell(0, 0), 1)
        self.assertEquals(tuple(test_table.row(0)), (1, u"Sam", 1))

        # Pure SQL Query
        s = SQL("test", "sql_1", "select * from student order by id")
        s(ctx)
        records = ctx["sql_1"]
        self.assertEquals(records[0], (1, "Sam", "SamChi", 1))

        def my_row_handler(row):
            return Student(id=row[0], name=row[1],
                           fullname=row[2], grade=row[3])

        s = SQL("test", "sql_2", "select * from student where id > :id",
                {"id": 1}, row_handler=my_row_handler)
        s(ctx)
        records = ctx["sql_2"]
        self.assertEquals((records[0].id, records[0].name), (2, "Jack"))

        # Table Wrapper
        s = SQL("test", "sql_3", "select * from student order by id",
                result_wrapper=TableWrapper("students",
                                            (
                                                Title("id", u"编号"),
                                                Title("name", u"名字"),
                                                Title("fullname", u"全名"),
                                                Title("grade", u"年级")
                                            ))
                )
        s(ctx)
        table = ctx["sql_3"]
        row = table[0]
        self.assertEquals((row.id, row.name), (1, "Sam"))

        # 测试非查询语句
        s = SQL("test", None,
                (
                    "insert into student (id, name, fullname, grade) "
                    "values (:id, :name, :fullname, :grade)"
                ),
                {"id": 4, "name": "Jane", "fullname": "JaneGreen", "grade": 3})
        s(ctx)
        SQL("test", "sql_4", "select * from student where id = 4")(ctx)
        self.assertEquals(ctx["sql_4"][0], (4, "Jane", "JaneGreen", 3))

        # Test Plugin
        plugin_manager.sys_prepare(self.config)
        orm_query = plugin_manager.plugin("orm_query")
        orm_query.execute(
            ctx,
            Query("test", "result_1", (Student.id, Student.name), "id = 1"),
            Query("test", "result_2", (Student.id, Student.name), "id = 2")
        )
        result_1, result_2 = ctx["result_1"], ctx["result_2"]
        self.assertEquals([(1, "Sam")], result_1)
        self.assertEquals([(2, "Jack")], result_2)

    def _check_students_list(self, students):
        self.assertEquals(len(students), 3)
        self.assertEquals([std.name for std in students],
                          ["Sam", "Jack", "Betty"])


class KeyExtratcWrapperTestCase(GirlFriendTestCase):

    def test_wrap_collection_row(self):
        table = (
            (1, "Sam", 26, "A"),
            (2, "Jack", 25, "A"),
            (3, "Peter", 26, "B")
        )

        result = KeyExtractWrapper(0)(table)
        self.assertEquals(
            result,
            {
                1: (1, "Sam", 26, "A"),
                2: (2, "Jack", 25, "A"),
                3: (3, "Peter", 26, "B")
            }
        )

        table = (
            {"id": 1, "name": "Sam", "grade": "A"},
            {"id": 2, "name": "Jack", "grade": "B"}
        )

        result = KeyExtractWrapper("name")(table)
        self.assertEquals(
            result,
            {
                "Sam": {"id": 1, "name": "Sam", "grade": "A"},
                "Jack": {"id": 2, "name": "Jack", "grade": "B"}
            }
        )

    def test_wrap_object(self):
        table = (
            Grade(id=1, name="A"),
            Grade(id=2, name="B")
        )

        result = KeyExtractWrapper("id")(table)
        self.assertEquals(
            result,
            {
                1: table[0],
                2: table[1]
            }
        )

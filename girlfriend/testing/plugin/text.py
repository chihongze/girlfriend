# coding: utf-8

import re
import os
import os.path
from girlfriend.testing import GirlFriendTestCase
from girlfriend.plugin.text import TextR
from girlfriend.data.table import TableWrapper
from girlfriend.util.lang import args2fields

log_content = r"""2016-03-03 11:03:37,867 - girlfriend - INFO - 工作流开始执行，起始点为 'read_json'
2016-03-03 11:03:37,867 - girlfriend - INFO - 开始执行工作单元 read_json [job]
2016-03-03 11:03:37,868 - girlfriend - INFO - 工作单元 read_json [job] 执行完毕
2016-03-03 11:03:37,868 - girlfriend - INFO - 开始执行工作单元 orm_query [job]
2016-03-03 11:03:37,881 - girlfriend - ERROR - 系统错误，工作流被迫中止
Traceback (most recent call last):
  File "/girlfriend/workflow/gfworkflow.py", line 399, in execute
    last_result = current_unit.execute(ctx)
  File "/girlfriend/workflow/gfworkflow.py", line 181, in execute
    return self._execute(context, self._args)
  File "/girlfriend/workflow/gfworkflow.py", line 193, in _execute
    result = executable(context, *args)
  File "/girlfriend/plugin/__init__.py", line 372, in execute
    return self._execute(context, *args, **kws)
  File "/girlfriend/plugin/orm.py", line 216, in execute
    return [exec_(context) for exec_ in exec_list]
  File "/girlfriend/plugin/orm.py", line 356, in __call__
    return self._execute_select_statement(session, context)
  File "/girlfriend/plugin/orm.py", line 376, in _execute_select_statement
    result_proxy = session.execute(self._sql, self._params)
  File "/sqlalchemy/orm/session.py", line 1034, in execute
    bind, close_with_result=True).execute(clause, params or {})
  File "/sqlalchemy/engine/base.py", line 914, in execute
    return meth(self, multiparams, params)
  File "/sqlalchemy/sql/elements.py", line 323, in _execute_on_connection
    return connection._execute_clauseelement(self, multiparams, params)
  File "/sqlalchemy/engine/base.py", line 1010, in _execute_clauseelement
    compiled_sql, distilled_params
  File "/sqlalchemy/engine/base.py", line 1146, in _execute_context
    context)
  File "/sqlalchemy/engine/base.py", line 1341, in _handle_dbapi_exception
    exc_info
  File "/sqlalchemy/util/compat.py", line 199, in raise_from_cause
    reraise(type(exception), exception, tb=exc_tb)
  File "/sqlalchemy/engine/base.py", line 1139, in _execute_context
    context)
  File "/sqlalchemy/engine/default.py", line 450, in do_execute
    cursor.execute(statement, parameters)
OperationalError: (sqlite3.OperationalError) no such column: cat_num"""


class TextRTestCase(GirlFriendTestCase):

    def setUp(self):
        with open("test.log", "w") as f:
            f.write(log_content)

    def test_read_one_line(self):
        # only read line
        ctx = self.workflow_context()
        records = TextR(filepath="test.log", record_matcher="line")(ctx)
        self.assertEquals(len(records), len(log_content.splitlines()))
        self.assertTrue(records[-1].startswith("OperationalError:"))

        # with max lines
        records = TextR(
            filepath="test.log", record_matcher="line", max_line=2)(ctx)
        self.assertEquals(len(records), 2)

        # with record_filter and record_handler
        records = TextR(
            filepath="test.log",
            record_matcher="line",
            record_filter=lambda line: bool(re.search("^2016", line)),
            record_handler=lambda line: tuple(line.split(" - "))
        )(ctx)
        self.assertEquals(records[-1][1:3], (u"girlfriend", u"ERROR"))

        # with result wrapper
        table = TextR(
            filepath="test.log",
            record_matcher="line",
            record_filter=lambda line: bool(re.search("^2016", line)),
            record_handler=lambda line: tuple(line.split(" - ")),
            result_wrapper=TableWrapper(
                "log_table",
                ("time", u"时间", "logger", u"日志", "level", u"级别", "msg", u"信息")
            )
        )(ctx)

        print
        print table
        self.assertEquals(
            table[0][("logger", "level")], (u"girlfriend", u"INFO"))

        # with pointer
        records = TextR(
            filepath="test.log",
            record_matcher="line",
            pointer="test_pointer"
        )(ctx)
        with open("test.log", "a") as f:
            for i in xrange(0, 10):
                f.write(str(i) + "\n")
        records = TextR(
            filepath="test.log",
            record_matcher="line",
            record_handler=int,
            pointer="test_pointer"
        )(ctx)
        self.assertEquals(records, range(0, 10))

        # with file change
        with open("test.log", "a") as f:
            for i in xrange(10, 20):
                f.write(str(i) + "\n")
        os.rename("test.log", "test.log.bak")
        with open("test.log", "w") as f:
            for i in xrange(20, 30):
                f.write(str(i) + "\n")
        records = TextR(
            filepath="test.log",
            record_matcher="line",
            record_handler=int,
            pointer="test_pointer",
            change_file_logic=lambda ctx: "test.log.bak"
        )(ctx)
        self.assertEquals(records, range(10, 30))

    def test_with_record_matcher(self):
        ctx = self.workflow_context()

        def logger_record_matcher(ctx):
            if "ERROR" in ctx.current_line:
                tb_lines = ctx.prepare_read(
                    lambda line: not line.startswith("2016"))
                ctx.add()
                ctx.add(tb_lines)
                ctx.end()
            elif "INFO" in ctx.current_line:
                ctx.add()
                ctx.end()

        class Log(object):

            @staticmethod
            def from_record(record_buffer):
                if len(record_buffer) == 1:
                    return Log(*record_buffer[0].split(" - "))
                elif len(record_buffer) == 2:
                    return Log(*record_buffer[0].split(" - "),
                               tb=record_buffer[1])

            @args2fields(False)
            def __init__(self, time, logger, level, msg, tb=None):
                pass

        records = TextR(
            filepath="test.log",
            record_matcher=logger_record_matcher,
            record_handler=Log.from_record
        )(ctx)
        self.assertEquals([r.level for r in records], ["INFO"] * 4 + ["ERROR"])
        self.assertTrue(records[-1].tb[-1].startswith("OperationalError"))

    def tearDown(self):
        if os.path.exists("test.log"):
            os.remove("test.log")
        if os.path.exists("test_pointer"):
            os.remove("test_pointer")
        if os.path.exists("test.log.bak"):
            os.remove("test.log.bak")

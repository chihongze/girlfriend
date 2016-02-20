# coding: utf-8

import os
import xlrd
import os.path
from girlfriend.data.table import ListTable, Title
from girlfriend.testing import GirlFriendTestCase
from girlfriend.plugin.excel import (
    ExcelWriterPlugin,
    SheetW,
    CellStyle,
    ExcelReaderPlugin,
    SheetR,
)


class ExcelWriterPluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.students_list = (
            (1, u"迟宏泽", u"男", 1),
            (2, "Jack", u"男", 2),
            (3, u"韩梅梅", u"女", 3),
            (5, u"李雷", u"男", 3)
        )
        self.students_table = ListTable(
            "students",
            (
                Title("id", u"编号"),
                Title("name", u"姓名"),
                Title("gender", u"性别"),
                Title("grade", u"年级")
            ),
            self.students_list
        )

        def even_row(row_index, column_index):
            return row_index != 0 and row_index % 2 == 0

        self.even_row_style = CellStyle(even_row, {"font_color": "red"})
        self.top_three_style = CellStyle(
            ((1, 3), None), {"bg_color": "yellow"})

        self.tmp_path = []

    def test_write_table(self):
        ctx = {}
        excel_writer = ExcelWriterPlugin()

        # write to tmp
        path = excel_writer.execute(
            ctx, None,
            sheets=(SheetW(self.students_table),)
        )
        workbook = xlrd.open_workbook(path)
        self.tmp_path.append(path)
        self._check_table_workbook(workbook)

        # write to StringIO
        excel_writer.execute(
            ctx, "memory:students_xlsx",
            sheets=(SheetW(self.students_table),)
        )
        book_buffer = ctx["students_xlsx"]
        book_buffer.seek(0)
        workbook = xlrd.open_workbook(file_contents=book_buffer.buf)
        self._check_table_workbook(workbook)

        # write to target file

        def draw_chart(workbook, sheet):
            """绘制图表
            """
            chart = workbook.add_chart({"type": "column"})
            chart.add_series({
                "categories": "=students! $B$2: $B$5",
                "values": "=students! $D$2: $D$5",
            })
            sheet.insert_chart("A6", chart)

        path = excel_writer.execute(
            ctx, os.path.expanduser("~/hehe2.xlsx"),
            sheets=(
                SheetW(
                    self.students_table, style=[
                        CellStyle(0, {"bold": True}),
                        self.even_row_style,
                        self.top_three_style
                    ],
                    sheet_handler=draw_chart
                ),
            ))
        workbook = xlrd.open_workbook(path)

        # write sequence
        excel_writer.execute(
            ctx, "memory:students_xlsx",
            sheets=(SheetW(self.students_list, sheet_name="std"),))
        book_buffer = ctx["students_xlsx"]
        book_buffer.seek(0)
        workbook = xlrd.open_workbook(file_contents=book_buffer.buf)
        student_table = workbook.sheet_by_name("std")
        self.assertEquals(student_table.nrows, len(self.students_list))

    def _check_table_workbook(self, workbook):
        self.assertEquals(len(workbook.sheets()), 1)
        student_table = workbook.sheet_by_name("students")
        self.assertEquals(
            student_table.nrows, len(self.students_table) + 1)
        self.assertEquals(
            student_table.ncols, len(self.students_table.titles))

    def tearDown(self):
        for path in self.tmp_path:
            os.remove(path)


class ExcelReaderPluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.students = (
            (1, "Sam", 1),
            (2, "Jack", 2),
            (3, "James", 2),
            (4, "Peter", 1)
        )
        self.students_table = ListTable(
            "students",
            (
                Title("id", u"编号"),
                Title("name", u"姓名"),
                Title("grade", u"年级")
            ),
            self.students
        )

        self.scores = (
            (1, 100, 98, 88),
            (2, 95, 99, 99),
            (3, 96, 97, 89),
            (4, 98, 97, 99)
        )
        self.score_table = ListTable(
            "students_score",
            (
                Title("id", u"编号"),
                Title("c", u"C语言"),
                Title("java", u"Java程序设计"),
                Title("ds", u"数据结构")
            ),
            self.scores
        )

        excel_writer = ExcelWriterPlugin()
        self.path = excel_writer.execute({}, None, sheets=(
            SheetW(self.students_table),
            SheetW(self.score_table)
        ))

    def test_read_table(self):
        excel_reader = ExcelReaderPlugin()
        ctx = {}
        excel_reader.execute(
            ctx, self.path,
            SheetR("students", variable="students", skip_first_row=True),
            SheetR("students_score", variable="scores", skip_first_row=True)
        )
        students, scores = ctx["students"], ctx["scores"]
        self.assertEquals(len(students), len(self.students))
        self.assertEquals(len(scores), len(self.scores))

    def tearDown(self):
        os.remove(self.path)

# coding: utf-8

import xlrd
import time
import random
import types
import xlsxwriter
from StringIO import StringIO
from girlfriend.util.lang import (
    args2fields,
    SequenceCollectionType
)
from girlfriend.data.table import AbstractTable
from girlfriend.plugin.data import AbstractDataReader


class ExcelReaderPlugin(object):

    """该插件读取Excel文件，并转换为需要的数据结构
    """

    name = "read_excel"

    def execute(self, context, filepath, *sheet_readers):
        workbook = xlrd.open_workbook(filepath)
        return [reader(context, workbook) for reader in sheet_readers]


class SheetR(AbstractDataReader):

    """读取Sheet"""

    @args2fields()
    def __init__(self, sheetname, record_handler=None, record_filter=None,
                 result_wrapper=None, skip_first_row=False, variable=None):
        pass

    def __call__(self, context, workbook):
        worksheet = workbook.sheet_by_name(self._sheetname)
        result = []
        for row_index in xrange(0, worksheet.nrows):
            if self._skip_first_row and row_index == 0:
                continue
            record = [None] * worksheet.ncols
            for column_index in xrange(0, worksheet.ncols):
                value = worksheet.cell(row_index, column_index).value
                record[column_index] = value
            self._handle_record(record, result.append)
        return self._handle_result(context, result)


class ExcelWriterPlugin(object):

    """该插件输出xlsx格式文件
    """

    name = "write_excel"

    def execute(self, context, filepath, sheets=None, workbook_handler=None):
        if filepath is None:
            # 不指定则随机生成文件名
            filepath = "/tmp/{}_{}.xlsx".format(
                int(time.time()), random.randint(100, 999))
            workbook = xlsxwriter.Workbook(filepath)
        elif filepath.startswith("memory:"):
            output = StringIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            context[filepath[len("memory:"):]] = output
        else:
            workbook = xlsxwriter.Workbook(filepath)

        for sheet in sheets:
            sheet(context, workbook)

        if workbook_handler:
            workbook_handler(workbook)

        workbook.close()
        return filepath


class SheetW(object):

    """写入Sheet"""

    @args2fields()
    def __init__(self, table=None, sheet_name=None,
                 style=None, sheet_handler=None):
        pass

    def __call__(self, context, workbook):
        if isinstance(self._table, types.StringTypes):
            self._table = context[self._table]
        sheet = self._generate_sheet(workbook)
        if self._table is not None:
            if isinstance(self._table, AbstractTable):
                self._handle_table(sheet, workbook)
            else:
                self._handle_sequence(sheet, workbook)
        if self._sheet_handler:
            self._sheet_handler(workbook, sheet)

    def _handle_table(self, sheet, workbook):
        # 先写入标题
        for idx, title in enumerate(self._table.titles):
            style = self._get_style(0, idx, workbook)
            sheet.write(0, idx, title.title, style)
        self._handle_sequence(sheet, workbook, start=1)

    def _handle_sequence(self, sheet, workbook, start=0):
        for row_index, row in enumerate(self._table, start=start):
            for column_index, column in enumerate(row):
                style = self._get_style(row_index, column_index, workbook)
                sheet.write(row_index, column_index, column, style)

    def _get_style(self, row_index, column_index, workbook):

        if not self._style:
            return None

        style = {}
        for s in self._style:
            if s.match(row_index, column_index):
                style.update(s.style_dict)
        if style:
            return workbook.add_format(style)
        else:
            return None

    def _generate_sheet(self, workbook):
        sheet_name = None
        if self._sheet_name:
            sheet_name = self._sheet_name
        else:
            sheet_name = self._table.name
        if sheet_name is None:
            return workbook.add_worksheet()
        else:
            return workbook.add_worksheet(sheet_name)


class CellStyle(object):

    """单元格样式"""

    def __init__(self, selector, style_dict):
        self._selector = selector
        self._style_dict = style_dict
        self._formatter = None

    def match(self, row_index, column_index):
        if isinstance(self._selector, types.FunctionType):
            return self._selector(row_index, column_index)
        elif isinstance(self._selector, int):
            return row_index == self._selector
        elif isinstance(self._selector, SequenceCollectionType):
            row_condition, column_condition = self._selector
            row_matched, column_matched = (
                self._match(row_index, row_condition),
                self._match(column_index, column_condition)
            )
            return row_matched and column_matched

    def _match(self, index, condition):
        if condition is None:
            return True
        if isinstance(condition, int):
            return index == condition
        elif isinstance(condition, SequenceCollectionType):
            return condition[0] <= index <= condition[-1]

    @property
    def style_dict(self):
        return self._style_dict

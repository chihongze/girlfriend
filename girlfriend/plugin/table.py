# coding: utf-8

import re
import types
import prettytable
from collections import defaultdict
from girlfriend.data.table import (
    AbstractTable,
    TableWrapper,
    Title,
    ListTable
)
from girlfriend.util.lang import (
    args2fields,
    SequenceCollectionType
)
from girlfriend.exception import (
    InvalidTypeException,
    InvalidArgumentException
)


class TableAdapterPlugin(object):

    """将上下文中的二维列表、对象列表、字典列表适配成Table对象
       使用方法:

       Job("table_adapter", args=(
            TableMeta("test", "test_table", u"测试表",
                     (Title("id"), Title("name")))
       ))
    """

    name = "table_adapter"

    def __init__(self):
        pass

    def execute(self, context, *table_metas):
        return [table_meta(context) for table_meta in table_metas]


class TableMeta(object):

    """装载Table元数据，并对ctx_variable进行转换
    """

    @args2fields()
    def __init__(self, from_variable, to_variable,
                 name, titles, table_type=None):
        """
        :param from_variable 要转换为table对象的context变量名
        :param to_variable   转换结果的对象变量名
        :param name          表格名称
        :param titles        表格标题列表
        :param table_type    表格类型，默认为自动推断
        """
        pass

    def __call__(self, context):
        if isinstance(self._from_variable, types.StringTypes):
            # 如果是字符串，那么将作为上下文变量名，直接从context中获取变量
            obj = context[self._from_variable]
            table = TableWrapper(
                self._name,
                self._titles,
                self._table_type)(obj)
            context[self._to_variable] = table
            return table
        elif isinstance(self._from_variable, SequenceCollectionType):
            # 如果是List或者Tuple类型，那么从头构造数据
            table_data = []
            for row in self._from_variable:
                if isinstance(row, SequenceCollectionType):
                    row_data = []
                    for element in row:
                        if isinstance(element, types.StringTypes) \
                                and element.startswith("$"):
                            element = context[element[1:]]
                        row_data.append(element)
                    table_data.append(row_data)
                elif (isinstance(row, types.StringTypes) and
                      row.startswith("$")):
                    row = context[row[1:]]
                    table_data.append(row)
                else:
                    table_data.append(row)
            table = TableWrapper(
                self._name,
                self._titles,
                self._table_type
            )(table_data)
            context[self._to_variable] = table
            return table


class TableColumn2TitlePlugin(object):

    """该插件可以将table对象的某一列值转换成行，例如，我们从数据库中得到每人每周得分的结果，
       通常是这种结构:

       id week name grade score
        1   1   Jack  1    95
        1   2   Jack  1    97
        1   3   Jack  1    94
        1   4   Jack  1    87
        2   1   Sam   2    86
        2   2   Sam   2    87
        2   3   Sam   2    96

        但很多时候为了方便横向比较，我们最终通常需要这样的格式：

        id name grade week_1 week_2 week_3 week_4
         1  Jack  1     95     97     94     87
         2  Sam   2     86     87     96     99

        该插件可以帮助快速完成此类工作
    """

    name = "column2title"

    def execute(self, context, from_table, to_table,
                title_column, value_column, title_generator=Title,
                new_title_sort=sorted, new_table_name=None, default=None,
                sum_title=None, avg_title=None):
        """
        :param context  上下文对象
        :param from_table  要转换的表，可以是具体的table对象，也可以是上下文变量名
        :param to_table  转换结果所保存的变量名
        :param title_column  要转换为标题的列，比如上例中的week
        :param value_column  为新列提供数据的列，比如上例中的score
        :param title_generator 新列生成器，接受一个列值作为参数，返回Title对象
                         例如: lambda week: Title("week_" + week, u"星期" + week)
        :param new_title_sort 新标题排序，接受新标题值的列表，返回排序后的结果
        :param sum_title 接受一个Title对象，如果不为None，那么将用此列保存合计
        :param avg_title 平均值
        """
        if isinstance(from_table, types.StringTypes):
            from_table = context[from_table]

        title_column_values = set()

        # 将title_column和value_column之外的列作为唯一列
        unique_fields = tuple(title.name for title in from_table.titles
                              if title.name != title_column and
                              title.name != value_column)

        tmp_result = defaultdict(dict)
        for row in from_table:
            unique_columns = row[unique_fields]
            title_column_value = row[title_column]
            new_column_value = row[value_column]
            tmp_result[unique_columns][title_column_value] = new_column_value
            title_column_values.add(title_column_value)

        # 生成标题列表
        title_column_values = new_title_sort(title_column_values)
        titles = [title for title in from_table.titles
                  if title.name != title_column and
                  title.name != value_column]
        titles.extend(title_generator(v) for v in title_column_values)

        if sum_title:
            titles.append(sum_title)
        if avg_title:
            titles.append(avg_title)

        table_name = (from_table.name
                      if new_table_name is None else new_table_name)

        data = []
        for unique_columns in tmp_result:
            row = []
            row.extend(unique_columns)
            series = tuple(tmp_result[unique_columns].get(col, default)
                           for col in title_column_values)
            row.extend(series)
            sum_value = None
            if sum_title:
                sum_value = sum(series)
                row.append(sum_value)
            if avg_title:
                if sum_value is None:
                    sum_value = sum(series)
                avg_value = sum_value / len(series)
                row.append(avg_value)
            data.append(row)

        context[to_table] = ListTable(table_name, titles, data)


ZH_MONTHS = (u"一", u"二", u"三", u"四", u"五", u"六",
             u"七", u"八", u"九", u"十", u"十一", u"十二")


def ZhMonthGenerator(month):
    return Title("month_" + str(month), ZH_MONTHS[month - 1] + u"月")


class PrintTablePlugin(object):

    """以MySQL表格的样式批量打印Table对象
    """

    name = "print_table"

    def execute(self, context, *tables):
        for table in tables:
            if isinstance(table, types.StringTypes):
                table = context[table]
            # 居中显示表格名称
            print table.name.center(100, "-")
            print "\n"
            ptable = prettytable.PrettyTable([t.title for t in table.titles])
            for row in table:
                ptable.add_row(row)
            print str(ptable)
            print "\n\n"


class HTMLTablePlugin(object):

    name = "html_table"

    def execute(self, context, *table_formatters):
        return [formatter(context) for formatter in table_formatters]


class HTMLTable(object):

    """HTML格式化单元
    """

    @args2fields()
    def __init__(self, table, variable=None, property=None):
        pass

    def __call__(self, context):

        if isinstance(self._table, types.StringTypes):
            self._table = context[self._table]

        # table element
        html_buffer = [u"<table {prop}>".format(
            prop=self._extract_properties("table", value=self._table)
        )]

        # thead element
        html_buffer.append(u"<thead>")

        # thead -> tr
        html_buffer.append(
            u"<tr {prop}>".format(
                prop=self._extract_properties("title-row", value=self._table)
            )
        )

        # thead -> tr -> td
        for column_index, title in enumerate(self._table.titles):
            html_buffer.append(
                u"<th {prop}>{t}</th>".format(
                    t=title.title,
                    prop=self._extract_properties(
                        "title-cell", column_index=column_index, value=title)
                )
            )

        # close thead
        html_buffer.append(u"</tr></thead>")

        # tbody
        html_buffer.append(u"<tbody>")

        # tbody tr
        for row_index, row in enumerate(self._table):
            html_buffer.append(
                u"<tr {prop}>".format(
                    prop=self._extract_properties(
                        "data-row", row_index=row_index, value=row)
                )
            )
            for column_index, title in enumerate(self._table.titles):
                col_value = row[title.name]
                html_buffer.append(
                    u"<td {prop}>{col}</td>".format(
                        prop=self._extract_properties(
                            "data-cell", row_index=row_index,
                            column_index=column_index,
                            field_name=title.name,
                            value=col_value),
                        col=col_value
                    )
                )
            html_buffer.append(u"</tr>")

        # finish tbody
        html_buffer.append(u"</tbody></table>")
        html_content = "".join(html_buffer)
        if self._variable:
            context[self._variable] = html_content
        return html_content

    def _extract_properties(self, element_type, row_index=None,
                            column_index=None, field_name=None, value=None):
        """提取元素属性
        """
        if not self._property:
            return ""
        properties = self._property.get(element_type)
        if not properties:
            return ""

        if isinstance(properties, types.FunctionType):
            if element_type == "table":
                properties = properties(value)
            elif element_type == "title-row":
                properties = properties(value)
            elif element_type == "title-cell":
                properties = properties(column_index, value)
            elif element_type == "data-row":
                properties = properties(row_index, value)
            elif element_type == "data-cell":
                properties = properties(
                    row_index, column_index, field_name, value)

        if not properties:
            return ""
        return properties


class ConcatTablePlugin(object):

    """将多个表格按纵轴拼接在一起，类似于关系数据库中的union操作
    """

    name = "concat_table"

    def execute(self, context, tables, name, titles=0, variable=None):
        """
        :param context 上下文对象
        :param name    表名
        :param titles  标题，可以是Title对象列表，也可以是数字，如果是数字那么将
                       使用对应的拼接表标题
        :param tables  要拼接的表格，接受三种格式:
                       1. 具体的Table对象
                       2. Table对象的上下文变量名
                       3. 元组，第一个元素为Table对象，后面为要拼接的属性名
        """

        result = []
        for idx, table in enumerate(tables):
            fields = []  # 要拼接的字段
            if isinstance(table, types.StringTypes):
                table = context[table]
                fields = [title.name for title in table.titles]
            elif isinstance(table, AbstractTable):
                fields = [title.name for title in table.titles]
            elif isinstance(table, SequenceCollectionType):
                table, fields = table[0], table[1:]
                if isinstance(table, types.StringTypes):
                    table = context[table]
            else:
                raise InvalidTypeException

            for row in table:
                result.append(row[fields])

            if isinstance(titles, int) and titles == idx:
                titles = [
                    title for title in table.titles if title.name in fields]

        if variable is None:
            return ListTable(name, titles, result)
        else:
            context[variable] = ListTable(name, titles, result)


class JoinTablePlugin(object):

    """join tables like relation database
    """

    name = "join_table"

    def execute(self, context, way, left, right, on, fields,
                name, titles=None, variable=None):
        """
        :param context 上下文对象
        :param way join方式，允许inner、left和right三种join方式
        :param on  join条件，left_column = right_column，多个条件用逗号隔开
        :param fields 结果字段
        :param name 结果表格名称
        :param titles 结果表格标题
        :param variable 用于存储的上下文变量
        """

        if way not in ("inner", "left", "right"):
            raise InvalidArgumentException(
                u"不合法的join方式'{}'，只支持inner、left、right三种join方式".format(way))

        conditions = self._parse_conditions(on)

        if isinstance(left, types.StringTypes):
            left = context[left]
        if isinstance(right, types.StringTypes):
            right = context[right]

        if way == "inner":
            result = self._inner_join(left, right, fields, conditions)
        elif way == "left":
            result = self._side_join("left", left, right, fields, conditions)
        elif way == "right":
            result = self._side_join("right", right, left, fields, conditions)

        if titles is None:
            titles = tuple(Title(f.split(".")[1]) for f in fields)

        table = ListTable(name, titles, result)
        if variable:
            context[variable] = table
        else:
            return table

    def _parse_conditions(self, on_conditions):
        """解析on条件表达式"""
        return [
            _JoinCondition.parse(statement)
            for statement in on_conditions.split(",")]

    def _inner_join(self, left_table, right_table, fields, conditions):
        left_fields = [c.left_field for c in conditions]
        right_fields = [c.right_field for c in conditions]

        right_table_hash = self._table_hash(
            right_table, right_fields)
        result = []

        for row in left_table:
            hash_code = hash(row[left_fields])
            right_row_index_list = right_table_hash[hash_code]
            if not right_row_index_list:
                continue

            for right_row_index in right_row_index_list:
                right_row = right_table[right_row_index]
                if row[left_fields] == right_row[right_fields]:
                    result.append(self._build_row(fields, row, right_row))
                    break
        return result

    def _side_join(self, way, main_table, sub_table, fields, conditions):

        left_fields = [c.left_field for c in conditions]
        right_fields = [c.right_field for c in conditions]

        if way == "left":
            main_fields, sub_fields = left_fields, right_fields
        elif way == "right":
            main_fields, sub_fields = right_fields, left_fields

        sub_table_hash = self._table_hash(sub_table, sub_fields)

        result = []

        for row in main_table:
            hash_code = hash(row[main_fields])
            sub_row_index_list = sub_table_hash[hash_code]

            if way == "left":
                left_row, right_row = row, None
            else:
                left_row, right_row = None, row

            if not sub_row_index_list:
                result.append(self._build_row(fields, left_row, right_row))
                continue

            missed = True
            for sub_row_index in sub_row_index_list:
                sub_row = sub_table[sub_row_index]
                if row[main_fields] == sub_row[sub_fields]:
                    if way == "left":
                        left_row, right_row = row, sub_row
                    else:
                        left_row, right_row = sub_row, row
                    result.append(self._build_row(fields, left_row, right_row))
                    missed = False
                    break

            if missed:
                result.append(self._build_row(fields, left_row, right_row))

        return result

    def _table_hash(self, table, fields):
        hash_row_dict = defaultdict(list)
        for idx, row in enumerate(table):
            hash_row_dict[hash(row[fields])].append(idx)
        return hash_row_dict

    def _build_row(self, fields, left_row, right_row):
        if not fields:
            return tuple(left_row) + tuple(right_row)
        row = []
        for field in fields:
            if field.startswith(("r.", "right.")):
                if right_row:
                    row.append(right_row[field.split(".")[1]])
                else:
                    row.append(None)
            elif field.startswith(("l.", "left.")):
                if left_row:
                    row.append(left_row[field.split(".")[1]])
                else:
                    row.append(None)
        return row


class _JoinCondition(object):

    """Join 条件"""

    PATTERN = re.compile(r"\s*([\w_]+)\s*=\s*([\w_]+)\s*")

    @classmethod
    def parse(cls, statement):
        match_result = _JoinCondition.PATTERN.search(statement)
        if not match_result:
            raise InvalidArgumentException(u"表达式'{}'格式不合法".format(statement))
        return cls(match_result.group(1), match_result.group(2))

    def __init__(self, left_field, right_field):
        self.left_field = left_field
        self.right_field = right_field


class SplitTablePlugin(object):

    """分割表插件，根据指定条件将一个Table对象分割成多个Table对象"""

    name = "split_table"

    def execute(self, context, table, split_condition, variable=None):
        """
        :param context 上下文对象
        :param table 要分割的table对象
        :param split_condition 接受一个函数对象，参数为一个行对象，结果返回两个值，
                               第一个为引用的key，第二个为表格名称
        :param variable 要保存到的上下文变量

        :return 返回一个字典对象，key为split_condition中返回的引用值，value为表格对象
        """
        result = {}

        for row in table:
            split_result = split_condition(row)
            if split_result is None:
                continue
            ref_key, sub_table_name = split_result
            if ref_key in result:
                sub_table = result[ref_key]
                sub_table.append(row.obj)
            else:
                sub_table = TableWrapper(
                    sub_table_name,
                    table.titles
                )([row.obj])
                result[ref_key] = sub_table

        if variable:
            context[variable] = result

        return result

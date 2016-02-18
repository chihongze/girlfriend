# coding: utf-8

import random
import webbrowser
from girlfriend.data.table import (
    Title,
    ListTable,
    TableWrapper
)
from girlfriend.plugin.table import (
    TableMeta,
    TableColumn2TitlePlugin,
    ZhMonthGenerator,
    PrintTablePlugin,
    ConcatTablePlugin,
    SplitTablePlugin,
    JoinTablePlugin,
    HTMLTable,
)
from girlfriend.testing import GirlFriendTestCase


class TableMetaTestCase(GirlFriendTestCase):

    def test_adapt_context_variable(self):
        """测试直接包装上下文变量
        """
        ctx = {
            "students": (
                (1, "Sam", 1),
                (2, "Jack", 2),
                (3, "James", 3)
            )
        }

        table_meta = TableMeta(
            "students",
            "students_table",
            u"学生表",
            ("id", u"编号", "name", u"姓名", "grade", u"年级")
        )

        table_meta(ctx)
        table = ctx["students_table"]
        self.assertEquals(len(table), 3)
        self.assertEquals(
            (table[1].id, table[1].name, table[1].grade),
            (2, "Jack", 2)
        )

    def test_adapt_list(self):
        """测试包装列表
        """

        ctx = {
            "total_students": 100,
            "new_students_by_year": 20,
            "jack_score": ["Jack", 120, 100, 101],
            "mike_score": ["Mike", 110, 109, 90]
        }

        table_meta = TableMeta(
            [("$total_students", "$new_students_by_year", 15, 5)],
            "summary_table",
            u"汇总表",
            (
                "total_students", u"学生总数",
                "new_students", u"新增学生数",
                "new_male", u"新增男生数",
                "new_female", u"新增女生数"
            )
        )

        table_meta(ctx)
        t = ctx["summary_table"]
        self.assertEquals(len(t), 1)
        self.assertEquals(
            (t[0].total_students, t[0].new_students,
             t[0].new_male, t[0].new_female),
            (100, 20, 15, 5)
        )

        table_meta = TableMeta(
            ["$jack_score", "$mike_score"],
            "score_table",
            u"成绩表",
            (
                "name", u"姓名",
                "chinese", u"语文",
                "maths", u"数学",
                "english", u"英语"
            )
        )

        table_meta(ctx)
        t = ctx["score_table"]
        self.assertEquals(len(t), 2)
        self.assertEquals(
            (t[0].name, t[0].chinese, t[0].maths, t[0].english),
            ("Jack", 120, 100, 101)
        )


class TableColumn2TitlePluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.ctx = {}
        titles = (
            Title("id", u"编号"),
            Title("name", u"姓名"),
            Title("grade", u"年级"),
            Title("month", u"月"),
            Title("score", u"得分")
        )

        students = (
            (1, "Sam", 1),
            (2, "James", 1),
            (3, "Joe", 2),
            (4, "Jack", 2)
        )

        data = []
        for i in xrange(0, len(students)):
            student = students[i]
            for m in xrange(1, 13):
                score = random.randint(0, 100)
                row = []
                row.extend(student)
                row.extend([m, score])
                data.append(row)
        random.shuffle(data)
        self.ctx["students_table"] = ListTable("students", titles, data)

    def test_transform(self):
        transformer = TableColumn2TitlePlugin()
        transformer.execute(
            self.ctx, "students_table", "changed_table",
            "month", "score", ZhMonthGenerator,
            sum_title=Title("sum", u"总分"),
            avg_title=Title("avg", u"平均分"))
        print "\nBefore change:"
        students_table = self.ctx["students_table"]
        print "\n"
        print students_table
        changed_table = self.ctx["changed_table"]
        print "\nAfter change:"
        print "\n"
        print changed_table


class PrintTablePluginTestCase(GirlFriendTestCase):

    def test_print(self):
        table = ListTable(
            "test",
            (
                Title("id", u"编号"),
                Title("name", u"姓名"),
                Title("grade", u"年级")
            ),
            (
                (1, "Sam", "A"),
                (2, "Tom", "A"),
                (3, "Jack", "B"),
                (4, "James", "C")
            )
        )

        pp = PrintTablePlugin()
        pp.execute(None, table, table, table)


class ConcatTablePluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.table_a = TableWrapper(
            "table_a",
            ("id", None, "name", None, "grade", None, "gender", None))((
                (1, "Sam", "A", "M"),
                (2, "Jack", "B", "M"),
                (3, "Lucy", "B", "F")
            ))

        self.table_b = TableWrapper(
            "table_b",
            ("id", None, "name", None, "grade", None, "gender", None))((
                (4, "James", "A", "M"),
                (5, "Peter", "A", "M")
            ))

        self.table_c = TableWrapper(
            "table_c", ("name", None, "grade", None, "gender", None))((
                ("Betty", "C", "F"),
                ("May", "C", "F")
            ))

    def test_concat(self):
        ctx = {}
        concat_table = ConcatTablePlugin()

        # titles is a number index
        table = concat_table.execute(
            ctx, (self.table_a, self.table_b),
            "concat_table"
        )

        print table

        self.assertEquals(len(table), 5)
        self.assertEquals(tuple(table[0]), (1, "Sam", "A", "M"))

        # 合并列数不相同的表
        table = concat_table.execute(
            ctx, (
                (self.table_a, "name", "grade", "gender"),
                (self.table_b, "name", "grade", "gender"),
                self.table_c
            ),
            "concat_table"
        )

        print table

        self.assertEquals(len(table), 7)
        self.assertEquals(tuple(table[0]), ("Sam", "A", "M"))


class JoinTablePluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.students_table = ListTable(
            "students",
            (Title("id", u"编号"), Title("name", u"姓名"),
             Title("grade", u"年级"), Title("city", u"城市"),
             Title("class", u"班级")),
            (
                (1, "Sam", 1, 1, 2),
                (2, "Jack", 1, 2, 3),
                (3, "Lucy", 2, 4, 1),
                (4, "James", 2, 3, 2),
                (5, "Larry", 2, 10, 3),
                (6, "Betty", 2, 10, 5),
            )
        )

        self.city_table = ListTable(
            "city",
            (Title("id", u"编号"), Title("name", u"名称")),
            (
                (1, "Pyongyang"),
                (2, "Beijing"),
                (3, "Shanghai"),
                (4, "Guangzhou"),
                (5, "Jinan")
            )
        )

        self.class_scores = ListTable(
            "class_score",
            (Title("grade", u"年级"), Title(
                "class", u"班级"), Title("score", u"分数")),
            (
                (1, 1, 10),
                (1, 2, 20),
                (1, 3, 30),
                (2, 1, 40),
                (2, 2, 50),
                (2, 3, 60)
            )
        )

    def test_inner_join(self):
        join_table = JoinTablePlugin()
        ctx = {}
        result = join_table.execute(
            ctx,
            "inner",
            self.students_table,
            self.city_table,
            on="city = id",
            fields=("l.id", "l.name", "r.name"),
            name=u"学生所在地",
            titles=(Title("id", u"编号"), Title(
                "name", u"姓名"), Title("city", u"城市"))
        )

        self.assertEquals(len(result), 4)
        row_0 = result[0]
        self.assertEquals(
            (row_0.id, row_0.name, row_0.city),
            (1, "Sam", "Pyongyang"),
        )

        print "\n"
        print result

        # mutli on conditions
        result = join_table.execute(
            ctx,
            "inner",
            self.students_table,
            self.class_scores,
            on="grade=grade,class=class",
            fields=("l.id", "l.name", "r.grade", "r.class", "r.score"),
            name=u"班级得分",
            titles=(Title("id", u"编号"), Title(
                "name", u"姓名"), Title("grade", u"年级"), Title("clazz", u"班级"),
                Title("score", u"评分"))
        )

        self.assertEquals(len(result), 5)
        row_0 = result[0]
        self.assertEquals(
            (row_0.id, row_0.name, row_0.grade, row_0.clazz, row_0.score),
            (1, "Sam", 1, 2, 20)
        )

        print "\n"
        print result

    def test_left_join(self):
        join_table = JoinTablePlugin()
        ctx = {}

        result = join_table.execute(
            ctx,
            "left",
            self.students_table,
            self.city_table,
            on="city=id",
            fields=("l.id", "l.name", "r.name"),
            name=u"学生所在地",
            titles=(Title("id", u"编号"), Title(
                "name", u"姓名"), Title("city", u"城市"))
        )

        self.assertEquals(len(result), 6)
        last_row = result[-1]
        self.assertEquals(
            (last_row.id, last_row.name, last_row.city),
            (6, "Betty", None)
        )

        print "\n"
        print result

        result = join_table.execute(
            ctx,
            "left",
            self.students_table,
            self.class_scores,
            on="grade=grade,class=class",
            fields=("l.id", "l.name", "l.grade", "l.class", "r.score"),
            name=u"班级得分",
            titles=(Title("id", u"编号"), Title(
                "name", u"姓名"), Title("grade", u"年级"),
                Title("clazz", u"班级"), Title("score", u"分数"))
        )

        self.assertEquals(len(result), 6)
        last_row = result[-1]
        self.assertEquals(
            (last_row.id, last_row.name, last_row.grade,
             last_row.clazz, last_row.score),
            (6, "Betty", 2, 5, None)
        )

        print "\n"
        print result


class SplitTablePluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.students_table = ListTable(
            "students",
            (
                Title("id", u"编号"),
                Title("name", u"姓名"),
                Title("grade", u"年级")
            ),
            (
                (1, "Sam", 1),
                (2, "Jack", 1),
                (3, "James", 1),
                (4, "Betty", 2),
                (5, "Tom", 2),
                (6, "Lucy", 2),
                (7, "Jason", 3),
            )
        )

    def test_split(self):
        ctx = {}
        split_table = SplitTablePlugin()

        def split_condition(row):
            return (
                "students_grade_{}".format(row.grade),
                u"{}年级学生".format(row.grade)
            )
        result = split_table.execute(ctx, self.students_table, split_condition)

        self.assertEquals(len(result["students_grade_1"]), 3)
        print "\n", result["students_grade_1"]
        self.assertEquals(len(result["students_grade_2"]), 3)
        print result["students_grade_2"]
        self.assertEquals(len(result["students_grade_3"]), 1)
        print result["students_grade_3"]


class HtmlTablePluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.table = ListTable(
            "student",
            (
                Title("id", u"编号"),
                Title("name", u"姓名"),
                Title("grade", u"年级")
            ),
            (
                (1, u"小王", 1),
                (2, u"小李", 1),
                (3, u"小明", 2)
            )
        )

        def data_row_style(row_index, row):
            if row.grade == 1:
                return "style='color:red;'"

        def data_cell_style(row_index, column_index, field_name, value):
            if field_name == "id":
                return "style='color:orange;'"

        def title_row_style(table):
            return "style='background-color:gray;'"

        def title_cell_style(column_index, title):
            if title.name == "name":
                return "style='text-decoration:underline;'"

        self.properties = {
            "table": "border=1",
            "title-row": title_row_style,
            "title-cell": title_cell_style,
            "data-row": data_row_style,
            "data-cell": data_cell_style,
        }

    def test_html_format(self):
        html_content = HTMLTable(
            self.table, "table", property=self.properties)({})
        with open("/tmp/table.html", "w") as f:
            f.write(html_content.encode("gbk"))
        webbrowser.open("file:///tmp/table.html")

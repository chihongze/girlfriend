# coding: utf-8

"""
该工作流可以快速将SQL导出为Excel表格，并通过邮件发送给目标用户
使用json格式的文件来描述SQL任务，例如：

# 该单元为SQL任务，db为连接的数据库，sql为要执行的SQL语句，table为表名称，同时会用作Excel Sheet名称
# titles 为表格各字段的名称，必须按照顺序
{
  "db": "user",
  "sql": "select id, email, cat_num from user",
  "table": "注册用户",
  "titles": ["编号", "姓名", "宠物猫数目"]
}
{
  "db": "product",
  "sql": "select id, name, sell_num from product",
  "table": "商品销售详情",
  "titles": ["编号", "姓名", "销售数目"]
}

# 该单元描述邮件发送详情，可选，server为要使用的smtp服务器，sender为发件人，receivers为收件人
  当receivers为逗号隔开的字符串时，会一并发送给所有的收件人，方便统一沟通，当receivers为数组时，会单独发给每个人
  content为html形式的邮件正文，table为要在正文显示的html表格
{
  "server": "test",
  "sender": "hongze.chi@gmail.com",
  "receivers": "chihz3800@163.com",
  "subject": "数据邮件",
  "content": "<h1>数据报表</h1>",
  "table": [0, 1],
}

# 该单元描述导出Excel文件，sheets为包含的数据库表，从0开始计数
{
  "workbook": "test.xlsx",
  "sheets": [0, 1]
}

使用方法：
    gf_workflow -m :sqlreport -t sqltask.json
"""

import argparse
import os.path
from girlfriend.data.table import TableWrapper
from girlfriend.util.script import show_msg_and_exit
from girlfriend.workflow.gfworkflow import Job, Decision
from girlfriend.plugin.json import JSONR
from girlfriend.plugin.orm import SQL
from girlfriend.plugin.excel import SheetW
from girlfriend.plugin.table import HTMLTable
from girlfriend.plugin.mail import Attachment


cmd_parser = argparse.ArgumentParser(description=__doc__.decode("utf-8"))
cmd_parser.add_argument("--task", "-t", dest="task", default="",
                        help=u"指定任务描述文件")
cmd_parser.add_argument("--print", "-p", dest="print_tables",
                        action="store_true", help=u"是否打印表格")


def workflow(options):
    # 检查配置文件
    if not options.task:
        show_msg_and_exit(u"必须指定一个任务描述文件，文件格式见帮助")
    if not os.path.exists(options.task):
        show_msg_and_exit(u"任务描述文件 '{}' 不存在".format(options.task))

    return (
        # 读取json格式的任务描述文件并保存到上下文
        Job(
            "read_json",
            args=(
                JSONR(options.task, "block",
                      result_wrapper=_task, variable="task"),
            )
        ),

        # 执行SQL语句
        Job(
            "orm_query",
            args=_gen_orm_query_args
        ),

        # 决定是否打印表格到终端
        Decision(
            "need_print",
            lambda ctx: "print_table"
            if options.print_tables else "need_write_excel"
        ),

        # print tables
        Job(
            "print_table",
            args="orm_query.result"
        ),

        # 决定是否要输出Excel
        Decision(
            "need_write_excel",
            lambda ctx: "write_excel"
            if ctx["task"].get("workbooks") else "need_send_mail",
        ),

        # 输出Excel
        Job(
            "write_excel",
            args=_gen_excel_args
        ),

        # 是否发送Email
        Decision(
            "need_send_mail",
            lambda ctx: "need_render_html"
            if ctx["task"].get("mail") else "end"
        ),

        # 是否需要渲染html表格
        Decision(
            "need_render_html",
            lambda ctx: "html_table"
            if ctx["task"]["mail"].get("tables") else "send_mail"
        ),

        # 渲染html表格
        Job(
            "html_table",
            args=lambda ctx: [HTMLTable(
                ctx["orm_query.result"][idx],
                property=ctx["task"]["mail"].get("table_property"))
                for idx in ctx["task"]["mail"]["tables"]]
        ),

        # 发送邮件了!
        Job(
            "send_mail",
            args=_gen_send_mail_args
        )
    )


def _task(records):
    task = {"sqltasks": [], "workbooks": []}
    for record in records:
        if "db" in record:
            task["sqltasks"].append(record)
        elif "server" in record:
            task["mail"] = record
        elif "workbook" in record:
            task["workbooks"].append(record)
    return task


def _gen_orm_query_args(ctx):
    sqltasks = ctx["task"]["sqltasks"]
    return [
        SQL(
            engine_name=t["db"],
            variable_name="table_%d" % idx,
            sql=t["sql"],
            result_wrapper=TableWrapper(t["table"], t["titles"],
                                        auto_title_name=True)
        ) for idx, t in enumerate(sqltasks)
    ]


def _gen_excel_args(ctx):
    tables = ctx["orm_query.result"]
    for idx, workbook in enumerate(ctx["task"]["workbooks"]):
        yield {
            "filepath": workbook["workbook"],
            "sheets": [SheetW(tables[i]) for i in workbook["sheets"]]
        }


def _gen_send_mail_args(ctx):
    args = {}
    args.update(ctx["task"]["mail"])
    tables = args.pop("tables", None)
    args.pop("table_property", None)
    if tables:
        content = args["content"]
        for html_table in ctx["html_table.result"]:
            content += (html_table + "<br/>")
        args["content"] = content
    args["attachments"] = [
        Attachment(w["workbook"], "application/octet-stream")
        for w in ctx["task"]["workbooks"]
    ]
    return args

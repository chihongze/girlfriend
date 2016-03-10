# coding: utf-8

from girlfriend.tools.code_template.workflow_template import PluginCodeMeta

all_meta = {

    # csv series
    "read_csv": PluginCodeMeta(
        plugin_name="read_csv",
        args_template="""[
                CSVR(
                  path="filepath",
                  record_handler=None,
                  record_filter=None,
                  result_wrapper=TableWrapper(
                        "table_name",
                        titles=[]
                  ),
                  dialect="excel",
                  variable=None
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.csv import CSVR",
            "from girlfriend.data.table import TableWrapper"
        ]
    ),
    "write_csv": PluginCodeMeta(
        plugin_name="write_csv",
        args_template="""[
                CSVW(
                  path="memory:",
                  object=None,
                  record_handler=None,
                  record_filter=None,
                  dialect="excel"
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.csv import CSVW",
        ]
    ),

    # excel series
    "read_excel": PluginCodeMeta(
        plugin_name="read_excel",
        args_template="""[
                "filepath",
                SheetR(
                  sheetname="",
                  record_handler=None,
                  record_filter=None,
                  result_wrapper=TableWrapper(
                        "table_name",
                        titles=[]
                  ),
                  skip_first_row=False,
                  variable=None
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.excel import SheetR",
            "from girlfriend.data.table import TableWrapper"
        ]
    ),
    "write_excel": PluginCodeMeta(
        plugin_name="write_excel",
        args_template="""{
                "filepath": "filepath",
                "sheets": (
                    SheetW(
                        table=None,
                        sheet_name=None,
                        style=None,
                        sheet_handler=None
                    ),
                ),
                "workbook_handler": None
            }""",
        auto_imports=[
            "from girlfriend.plugin.excel import SheetW"
        ]
    ),

    # json series
    "read_json": PluginCodeMeta(
        plugin_name="read_json",
        args_template="""[
                JSONR(
                    path="http address or filepath",
                    style="block or line or array",
                    record_handler=None,
                    record_filter=None,
                    result_wrapper=TableWrapper(
                            "table_name",
                            titles=[]
                    ),
                    variable=None
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.json import JSONR",
            "from girlfriend.data.table import TableWrapper"
        ]
    ),
    "write_json": PluginCodeMeta(
        plugin_name="write_json",
        args_template="""[
                JSONW(
                    path="http address or filepath",
                    style="object or line or array",
                    object=None,
                    record_handler=None,
                    record_filter=None,
                    http_method="post",
                    http_field=None,
                    variable=None
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.json import JSONW",
        ]
    ),

    # mail series
    "send_mail": PluginCodeMeta(
        plugin_name="send_mail",
        args_template="""{
                "server": "smtp_server",
                "receivers": [],
                "sender": "",
                "subject": "",
                "content": "",
                "encoding": "utf-8",
                "attachments": []
            }""",
        auto_imports=[
            "from girlfriend.plugin.mail import Attachment, Mail",
        ]
    ),

    # orm series
    "orm_query": PluginCodeMeta(
        plugin_name="orm_query",
        args_template="""[
                Query(
                    engine_name="",
                    variable_name="",
                    query_items="",
                    query=None,
                    order_by=None,
                    group_by=None,
                    params=None,
                    row_handler=None,
                    result_wrapper=TableWrapper(
                            "table_name",
                            titles=[]
                    )
                ),
                SQL(
                    engine_name="",
                    variable_name="",
                    sql="",
                    params=None,
                    row_handler=None,
                    result_wrapper=TableWrapper(
                            "table_name",
                            titles=[]
                    )
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.orm import Query, SQL",
            "from girlfriend.data.table import TableWrapper"
        ]
    ),

    # table series
    "table_adapter": PluginCodeMeta(
        plugin_name="table_adapter",
        args_template="""[
                TableMeta(
                    from_variable="",
                    to_variable="",
                    name="table name",
                    titles=[],
                    table_type=None
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.table import TableMeta",
        ]
    ),
    "column2title": PluginCodeMeta(
        plugin_name="column2title",
        args_template="""{
                "from_table": "",
                "to_table": "",
                "title_column": "",
                "value_column": "",
                "title_generator": Title,
                "new_title_sort": sorted,
                "new_table_name": None,
                "default": None,
                "sum_title": None,
                "avg_title": None
            }""",
        auto_imports=[
            "from girlfriend.data.table import Title",
        ]
    ),
    "print_table": PluginCodeMeta(
        plugin_name="print_table",
        args_template="""[
                "$table1",
                "$table2",
            ]""",
        auto_imports=[]
    ),
    "html_table": PluginCodeMeta(
        plugin_name="html_table",
        args_template="""[
                HTMLTable(
                    table="context variable or table object",
                    variable=None,
                    property={
                        "table": "",
                        "title-row": "",
                        "title-cell": "",
                        "data-row": "",
                        "data-cell": "",
                    }
                ),
            ]""",
        auto_imports=[
            "from girlfriend.plugin.table import HTMLTable",
        ]
    ),
    "concat_table": PluginCodeMeta(
        plugin_name="concat_table",
        args_template="""{
                "tables": [
                    ("table_variable", "concat fields"),
                ],
                "name": "new table name",
                "titles": 0,
                "variable": None
            }""",
        auto_imports=[]
    ),
    "join_table": PluginCodeMeta(
        plugin_name="join_table",
        args_template="""{
                "way": "inner or left or right",
                "left": "left table",
                "right": "right table",
                "on": "left_column=right_column;left_column=right_column",
                "fields": ["l.id", "r.name"],
                "name": "new table name",
                "titles": None,
                "variable": None
            }""",
        auto_imports=[]
    ),
    "split_table": PluginCodeMeta(
        plugin_name="split_table",
        args_template="""{
                "table": "$table_var",
                "split_condition": lambda row: None, "new table name",
                "variable": None
            }""",
        auto_imports=[]
    ),

    # text series
    "read_text": PluginCodeMeta(
        plugin_name="read_text",
        args_template="""[
                TextR(
                    filepath=None,
                    record_matcher="line",
                    record_handler=None,
                    record_filter=None,
                    pointer=None,
                    change_file_logic=None,
                    max_line=None,
                    result_wrapper=None,
                    variable=None
                )
            ]""",
        auto_imports=["from girlfriend.plugin.text import TextR"]
    ),
}

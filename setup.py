#! /usr/bin/env python
# coding: utf-8

import setuptools
from girlfriend import VERSION

install_requires = [
    "SQLAlchemy",
    "prettytable",
    "httpretty",
    "ujson",
    "termcolor",
    "requests",
    "fixtures",
    "stevedore",
    "XlsxWriter",
    "xlrd",
]

setuptools.setup(
    name="girlfriend",
    version=VERSION,
    author="Sam Chi",
    author_email="chihongze@gmail.com",
    description=(
        "A pure Python girlfriend "
        "she can help you build operation scripts, "
        "send data report, monitor the system "
        "and do a lot of things you undreamed!"
        "The most important, "
        "her heart(core lib) is all completely free!"
    ),
    license="MIT",
    packages=setuptools.find_packages("."),
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "gf_workflow = girlfriend.tools.gf_workflow:main",
            "gf_config = girlfriend.tools.gf_config:main",
            "gf_gen = girlfriend.tools.gf_gen:main",
            "gf_test_data = girlfriend.tools.gf_test_data:main"
        ],

        # builtin plugins
        "girlfriend.plugin": [
            # db plugin
            "orm_query = girlfriend.plugin.orm:OrmQueryPlugin",

            # table plugin
            "table_adapter = girlfriend.plugin.table:TableAdapterPlugin",
            "column2title = girlfriend.plugin.table:TableColumn2TitlePlugin",
            "print_table = girlfriend.plugin.table:PrintTablePlugin",
            "concat_table = girlfriend.plugin.table:ConcatTablePlugin",
            "join_table = girlfriend.plugin.table:JoinTablePlugin",
            "split_table = girlfriend.plugin.table:SplitTablePlugin",
            "html_table = girlfriend.plugin.table:HTMLTablePlugin",

            # json plugin
            "read_json = girlfriend.plugin.json:JSONReaderPlugin",
            "write_json = girlfriend.plugin.json:JSONWriterPlugin",

            # excel plugin
            "read_excel = girlfriend.plugin.excel:ExcelReaderPlugin",
            "write_excel = girlfriend.plugin.excel:ExcelWriterPlugin",

            # csv plugin
            "read_csv = girlfriend.plugin.csv:CSVReaderPlugin",
            "write_csv = girlfriend.plugin.csv:CSVWriterPlugin",

            # email plugin
            "send_mail = girlfriend.plugin.mail:SendMailPlugin",
        ],

        # builtin workflow
        "girlfriend.workflow": [
            "sqlreport = girlfriend.workflow.builtin:sqlreport",
        ],

        # Code Template
        "girlfriend.code_template": [
            "workflow = girlfriend.tools.code_template.workflow_template",
        ],

        # plugin code meta
        "girlfriend.plugin_code_meta": [
            (
                "builtin = "
                "girlfriend.tools.code_template.plugin_code_meta:all_meta"
            )
        ]

    },
)

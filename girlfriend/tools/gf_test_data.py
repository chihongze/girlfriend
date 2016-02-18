# coding: utf-8

"""该工具用于生成sqlite3测试数据
   用法：
   gf_test_data 在当前目录下生成数据文件
   gf_test_data -f /file/data 在指定目录下生成测试数据
"""

import os
import sys
import sqlite3
import os.path
import argparse
from girlfriend.util.script import show_msg_and_exit

CREATE_USER_TABLE = """
create table user (
  id integer primary key not null,
  email text not null,
  name text not null,
  login_date date not null
)
"""

CREATE_CAT_TABLE = """
create table cat (
  id integer primary key not null,
  name text not null,
  owner integer not null,
  birthday date not null
)
"""

INSERT_USER = (
    "insert into user "
    "(id, email, name, login_date) "
    "values "
    "(:id, :email, :name, :login_date)"
)

INSERT_CAT = (
    "insert into cat "
    "(id, name, owner, birthday) "
    "values "
    "(:id, :name, :owner, :birthday)"
)

USER_DATA = (
    {
        "id": 1,
        "email": "chihz3800@163.com",
        "name": "Sam",
        "login_date": "2011-01-01"
    },
    {
        "id": 2,
        "email": "peter@163.com",
        "name": "Peter",
        "login_date": "2013-04-05",
    }
)

CAT_DATA = (
    {
        "id": 1,
        "name": "Mimi",
        "owner": 1,
        "birthday": "2014-04-02"
    },
    {
        "id": 2,
        "name": "Dashuai",
        "owner": 2,
        "birthday": "2015-01-03"
    }
)


def main():
    cmd_options = _parse_cmd_args()
    if os.path.exists(cmd_options.data_file):
        answer = raw_input(
            u"数据文件 '{}' 已经存在，是否覆盖？(y/n)".format(
                cmd_options.data_file).encode("utf-8"))
        if answer == 'y':
            os.remove(cmd_options.data_file)
        else:
            exit(0)

    with sqlite3.connect(cmd_options.data_file) as conn:
        # 创建表
        conn.executescript(CREATE_USER_TABLE)
        conn.executescript(CREATE_CAT_TABLE)

        # 填充数据
        cursor = conn.cursor()
        cursor.executemany(INSERT_USER, USER_DATA)
        cursor.executemany(INSERT_CAT, CAT_DATA)

    show_msg_and_exit(u"测试数据文件 '{}' 已经创建完毕!".format(cmd_options.data_file),
                      "green")


def _parse_cmd_args():
    cmd_parser = argparse.ArgumentParser(description=__doc__.decode("utf-8"))
    cmd_parser.add_argument("--file", "-f", dest="data_file",
                            default=os.path.join(os.getcwd(), "gftest.db"),
                            help=u"数据文件路径")
    return cmd_parser.parse_known_args(sys.argv[1:])[0]

if __name__ == "__main__":
    main()

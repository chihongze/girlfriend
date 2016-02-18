# coding: utf-8

"""
该工具用于快速生成配置文件和用户工作目录
"""

import sys
import os.path
import argparse
from girlfriend import VERSION
from girlfriend.exception import GirlFriendBizException
from girlfriend.util import config, script
from girlfriend.util.file_template import Dir, File

WELCOME = """
=== Girl Friend ===

版本：{version}
Bug或者好的想法欢迎提交GitHub issue
或者发送邮件到 hongze.chi@gmail.com
谢谢 :)
""".format(version=VERSION)

HOME_WORKSPACE = os.path.join(os.environ["HOME"], ".gf")


def main():
    cmd_args = parse_cmd_args()
    try:
        if cmd_args.f:
            gen_config_file(cmd_args.f)
            script.show_msg_and_exit(
                u"已经成功创建配置文件'{}'".format(cmd_args.f), "green")
        else:
            gen_home_workspace()
            print WELCOME
            script.show_msg_and_exit(
                u"默认工作目录以及默认配置文件创建成功，请查看 '{}'".format(HOME_WORKSPACE),
                "green")
    except GirlFriendBizException as biz_e:
        script.show_msg_and_exit(unicode(biz_e), "yellow")
    except Exception as sys_e:
        script.show_traceback_and_exit(unicode(sys_e))


def parse_cmd_args():
    parser = argparse.ArgumentParser(description=__doc__.decode("utf-8"))
    parser.add_argument("-f", default="", help=u"生成配置文件的路径")
    ns = parser.parse_args(sys.argv[1:])
    return ns


def gen_config_file(file_path):
    """依据模板生成配置文件
       :param file_path 配置文件路径
    """
    path, filename = os.path.split(file_path)
    File(filename, content=config.CONFIG_EXAMPLE).makeme(path)


def gen_home_workspace():
    Dir(".gf", elements=(
        File("gf.cfg", content=config.CONFIG_EXAMPLE),
    )).makeme(os.environ["HOME"])

if __name__ == "__main__":
    main()

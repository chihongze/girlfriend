# coding: utf-8

"""GirlFriend需要很多第三方的代码支持，比如自定义的插件、工作流等等，
这些第三方的代码和项目往往都是固定的格式，因此完全可以通过填充模板的方式来减少工作量。
gf_gen就是这种根据据设定好的模板生成代码和项目结构的工具。

Usage:
    gf_gen -t TEMPLATE_MODULE -p PROJECT_DIR --other_tpl_args xxxx
"""

import os
import sys
import argparse
from girlfriend.util.module import load_module
from girlfriend.util.cmdargs import print_help
from girlfriend.util.script import show_msg_and_exit


def main():
    options = parse_cmd_args()
    tpl_module = load_module(options.template,
                             entry_point="girlfriend.code_template")
    if tpl_module is None:
        show_msg_and_exit(u"找不到模板模块 '{}'".format(options.template))

    tpl_options = None
    tpl_cmd_parser = getattr(tpl_module, "cmd_parser", None)
    if tpl_cmd_parser is not None:
        if options.show_args:
            print_help(tpl_cmd_parser)
            return
        tpl_options = tpl_cmd_parser.parse_known_args(sys.argv[1:])[0]

    tpl_module.gen(options.path, tpl_options)


def parse_cmd_args():
    cmd_parser = argparse.ArgumentParser(description=__doc__.decode("utf-8"))
    cmd_parser.add_argument("--template", "-t",
                            dest="template", help=u"模板路径")
    cmd_parser.add_argument("--path", "-p", dest="path",
                            default=os.getcwd(), help=u"项目生成路径")
    cmd_parser.add_argument("--show-args", dest="show_args",
                            action="store_true", help=u"显示模板参数说明")
    return cmd_parser.parse_known_args(sys.argv[1:])[0]

if __name__ == "__main__":
    main()

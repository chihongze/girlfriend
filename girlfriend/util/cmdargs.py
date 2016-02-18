# coding: utf-8

"""本模块提供命令行参数解析辅助工具
"""

from termcolor import colored
import argparse


def print_help(parser, color=None):
    """输出帮助信息"""
    help_text = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        option_strings = ",".join(action.option_strings)
        help_text.append(u"{}  {}".format(option_strings, action.help))
    print "\n", colored("\n".join(help_text), color)

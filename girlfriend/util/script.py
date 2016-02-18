# coding: utf-8

"""编写命令行脚本时使用的辅助工具
"""

import traceback
from termcolor import colored


def show_traceback_and_exit(msg=u"", color="red"):
    """当异常发生时显示堆栈并退出
    """
    print colored(msg, color)
    traceback.print_exc()
    exit(0)


def show_msg_and_exit(msg, color="red"):
    """显示消息并退出程序
    """
    print colored(msg, color)
    exit(0)

# coding: utf-8

import argparse
import os.path
from girlfriend.plugin import Plugin, PluginManager
from girlfriend.workflow.gfworkflow import Job
from girlfriend.workflow.protocol import Env

# cmd args parser
cmd_parser = argparse.ArgumentParser(u"加1减2")
cmd_parser.add_argument("--start-num", dest="start_num",
                        help=u"起始值", default="0")

# 插件
plugins = [
    "multiply",
]
plugin_manager = PluginManager()


def multiply(ctx, a, b):
    return a * b
plugin_manager.register(
    Plugin.wrap_function("multiply", "multiply number", multiply))


def add(ctx, a, b):
    return a + b
plugin_manager.register(Plugin.wrap_function("add", "add number", add))


def minus(ctx, a, b):
    result = a - b
    with open(os.path.expanduser("~/test_workflow.txt"), "a") as f:
        f.write("{}\n".format(result))
    return result
plugin_manager.register(Plugin.wrap_function("minus", "minus number", minus))

# 配置
config = {
    "test": {
        "test_a_item": "a",
        "test_b_item": "b"
    }
}


def _test_args(cmd_options):
    return {
        "add_one": {
            "a": 1000,
        },
        "minus_two": {
            "a": "$add_one.result"
        }
    }


def _product_args(cmd_options):
    return {
        "add_one": {
            "a": 2000,
        },
        "minus_two": {
            "a": "$add_one.result"
        }
    }

# environments
env = (
    Env("test", _test_args),
    Env("product", _product_args),
)


def args(cmd_options):
    # args generator
    return {
        "add_one": {
            "a": int(cmd_options.start_num),
        },
        "minus_two": {
            "a": "$add_one.result"
        }
    }


def test_multiply(context):
    multiply_plugin = context.plugin("multiply")
    print multiply_plugin.execute(
        context,
        context["add_one.result"],
        context["minus_two.result"]
    )

# workflow units
workflow = (
    Job("add_one", "add", args={"b": 1}),
    Job("minus_two", "minus", args={"b": 2}),
    Job("multiply", caller=test_multiply)
)

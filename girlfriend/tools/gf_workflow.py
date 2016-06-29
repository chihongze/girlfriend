# coding: utf-8

"""使用此工具，可以直接通过命令行来执行一个工作流

   gf_workflow -m workflow.py -c config_file -e test ...
"""

import sys
import argparse
import termcolor
import traceback

# gevent patch
try:

    def _parse_arguments():
        """解析gf_workflow自身参数"""
        parser = argparse.ArgumentParser(
            description=__doc__.decode("utf-8"))

        parser.add_argument(
            "--module", "-m", dest="module", help=u"包含工作流定义的模块")
        parser.add_argument("--config", "-c", dest="config",
                            help=u"配置文件，默认将使用HOME/.gf/gf.cfg",
                            default="default")
        parser.add_argument("--environ", "-e", dest="environ",
                            help=u"指定当前使用环境",
                            default="test")
        parser.add_argument("--path", "-p", dest="path",
                            help=u"指定PYTHONPATH，使用分号分割", default="")
        parser.add_argument("--run-mode", "-r", dest="run_mode",
                            help=(
                                u"once - 只运行一次, "
                                u"forever - 在循环中运行, "
                                u"interval:1m - 每隔一分钟运行一次"
                            ),
                            default="once")
        parser.add_argument("--show-args", dest="show_args",
                            action="store_true", help=u"显示工作流模块自定义参数")
        parser.add_argument("--pid", dest="pid", help=u"指定PID文件")
        parser.add_argument("--gevent-patch", dest="gevent_patch",
                            default=None,
                            help=(
                                u"Gevent补丁类型 可以指定all，也可以具体patch某些模块，"
                                u"dns,os,select,socket,ssl,subprocess,sys,"
                                u"thread,time patch多个模块请使用逗号分隔"
                            ))

        return parser.parse_known_args(sys.argv[1:])[0]

    from gevent import monkey
    TOOLS_OPTIONS = _parse_arguments()
    gevent_patch = TOOLS_OPTIONS.gevent_patch

    if gevent_patch:
        gevent_patch = gevent_patch.strip()

    if gevent_patch == "all":
        monkey.patch_all()
        termcolor.cprint(u"Gevent patch all", "green")
    elif gevent_patch:
        patch_modules = [m.strip() for m in gevent_patch.split(",")]
        for patch_module in patch_modules:
            getattr(monkey, "patch_{}".format(patch_module))()
            termcolor.cprint(
                u"Gevent patch module: '{}'".format(patch_module), "green")
except SystemExit as e:
    if (e.code != 0):
        traceback.print_exc()
    exit(0)
except:
    traceback.print_exc()

import os
import imp
import time
import types
import os.path
import logging
import pkg_resources
from girlfriend.util.script import show_msg_and_exit
from girlfriend.util.config import Config
from girlfriend.util.cmdargs import print_help
from girlfriend.util.time import parse_time_unit
from girlfriend.util.logger import (
    create_logger,
    stdout_handler,
    daily_rotaiting_handler,
    get_logger_level_by_name,
)
from girlfriend.workflow.protocol import Env
from girlfriend.workflow.gfworkflow import Workflow, Context
from girlfriend.plugin import plugin_manager as DEFAULT_PLUGIN_MANAGER


# 插件管理器以及用到的插件名称
plugin_manager, plugin_names = None, None


def main():
    global TOOLS_OPTIONS
    config = Config.load_by_name(TOOLS_OPTIONS.config)
    _add_python_path(config)
    workflow_module = _load_module()

    workflow_parser = getattr(workflow_module, "cmd_parser", None)

    # 展示工作流模块所需要的参数说明
    if TOOLS_OPTIONS.show_args:
        _show_args(workflow_parser)

    # 解析workflow所需参数
    workflow_options = None
    if workflow_parser is not None:
        workflow_options = workflow_parser.parse_known_args(sys.argv[1:])[0]

    # 获取当前运行环境
    current_env = _get_current_env(workflow_module)

    # 更新配置信息，使用模块的配置项覆盖配置文件中的配置项
    _update_config(config, current_env, workflow_module, workflow_options)

    # 保存pid到文件
    if TOOLS_OPTIONS.pid:
        _save_pid_file(TOOLS_OPTIONS.pid)

    # 执行工作流
    _execute_workflow(config, workflow_module, workflow_options, current_env)


def _save_pid_file(pid_file_path):
    with open(pid_file_path, "w") as f:
        f.write(str(os.getpid()))


def _add_python_path(config):
    """添加PYTHONPATH"""
    python_path = TOOLS_OPTIONS.path
    if python_path:
        sys.path.extend(python_path.split(";"))
    python_path = config.get("workflow", "path")
    if python_path:
        sys.path.extend(python_path.split(";"))


def _load_module():
    """加载工作流模块"""
    module_path = TOOLS_OPTIONS.module

    if not module_path:
        show_msg_and_exit(u"必须使用-m参数指定一个工作流描述模块")

    if module_path.startswith(":"):
        module_path = module_path[1:]
        for ep in pkg_resources.iter_entry_points("girlfriend.workflow"):
            if ep.name == module_path:
                return ep.load()
        show_msg_and_exit(u"找不到工作流模块 '{}'".format(module_path))

    # 以.py结尾，那么按照python文件的形式进行加载
    elif module_path.endswith(".py"):
        if not os.path.exists(module_path):
            show_msg_and_exit(u"找不到工作流描述文件 '{}'".format(module_path))
        return imp.load_source("workflow", module_path)

    # 按照模块名称方式进行加载
    else:
        try:
            return __import__(module_path, fromlist=[""])
        except ImportError:
            show_msg_and_exit(u"找不到工作流模块 '{}'".format(module_path))


def _show_args(workflow_parser):
    """展示模块参数"""
    if workflow_parser is not None:
        print u"工作流的参数说明："
        print_help(workflow_parser)
        exit(0)
    else:
        print u"该工作流模块不需要参数"
        exit(0)


def _update_config(config, current_env, workflow_module, workflow_options):
    """更新配置信息，先按模块中的config变量进行更新，再按照具体的环境进行更新"""
    _update_config_items(config, getattr(workflow_module, "config", None),
                         workflow_options)
    _update_config_items(config, current_env.config, workflow_options)


def _update_config_items(config, new_config, workflow_options):
    if new_config is None:
        return
    if isinstance(new_config, types.FunctionType):
        new_config = new_config(workflow_options)
        if new_config is None:
            return
    config.update(new_config)


def _get_current_env(workflow_module):
    env_list = getattr(workflow_module, "env", None)
    if env_list is None:
        return Env.test_env()
    current_env_name = TOOLS_OPTIONS.environ
    for env in env_list:
        if env.name == current_env_name:
            return env
    show_msg_and_exit(u"找不到目标环境：'{}'".format(current_env_name))


def _execute_workflow(config, workflow_module, workflow_options, current_env):
    workflow_engine = _get_workflow_engine(
        config, workflow_module, workflow_options, current_env)

    # 一次性执行
    try:
        if TOOLS_OPTIONS.run_mode == "once":
            return _run_once(workflow_engine, config, workflow_module,
                             workflow_options, current_env)
        # 永久性执行
        elif TOOLS_OPTIONS.run_mode == "forever":
            _run_forever(workflow_engine, config, workflow_module,
                         workflow_options, current_env)
        # 按时间间隔执行
        elif TOOLS_OPTIONS.run_mode.startswith("interval:"):
            _run_interval(
                workflow_engine, config,
                workflow_module, workflow_options,
                current_env, TOOLS_OPTIONS.run_mode[len("interval:"):])
        else:
            print u"未知的运行模式：'{}'".format(TOOLS_OPTIONS.run_mode)
    finally:
        _clean_plugins(config)


def _run_interval(workflow_engine, config, workflow_module,
                  workflow_options, current_env, time_unit):
    """按周期运行"""
    sleeping_seconds = parse_time_unit(time_unit)
    while True:
        _run_once(workflow_engine, config, workflow_module,
                  workflow_options, current_env)
        time.sleep(sleeping_seconds)


def _run_forever(workflow_engine, config, workflow_module,
                 workflow_options, current_env):
    """永久运行"""
    while True:
        _run_once(workflow_engine, config, workflow_module,
                  workflow_options, current_env)


def _run_once(workflow_engine, config, workflow_module,
              workflow_options, current_env):
    runtime_args = _get_runtime_args(
        config, workflow_module, workflow_options, current_env)
    return workflow_engine.execute(runtime_args)


def _get_workflow_engine(config, workflow_module,
                         workflow_options, current_env):
    """获取工作流执行引擎"""

    # 获取工作单元列表
    workflow_list = getattr(workflow_module, "workflow", None)
    if not workflow_list:
        show_msg_and_exit(u"工作流单元列表不能为空")
    if isinstance(workflow_list, types.FunctionType):
        workflow_list = workflow_list(workflow_options)
        if not workflow_list:
            show_msg_and_exit(u"工作流单元列表不能为空")

    # 获取并初始化插件管理器
    global plugin_manager
    plugin_manager = getattr(
        workflow_module, "plugin_manager", DEFAULT_PLUGIN_MANAGER)
    global plugin_names
    plugin_names = set(work_unit.plugin_name for work_unit in workflow_list
                       if work_unit.unittype == "job" and
                       work_unit.plugin_name)
    # 额外插件列表
    extra_plugin_names = getattr(workflow_module, "plugins", tuple())
    for plugin_name in extra_plugin_names:
        plugin_names.add(plugin_name)
    plugin_manager.sys_prepare(config, *plugin_names)

    # 获取logger
    logger = getattr(workflow_module, "logger", None)
    if isinstance(logger, types.FunctionType):
        logger = logger(workflow_options)
    logger_level = getattr(workflow_module, "logger_level", logging.INFO)
    if isinstance(logger_level, types.FunctionType):
        logger_level = logger_level(workflow_options)
    if isinstance(logger_level, str):
        logger_level = get_logger_level_by_name(logger_level)
    if logger is None:
        logger = create_logger("girlfriend", (stdout_handler(),),
                               level=logger_level)
    elif isinstance(logger, str):
        logger = create_logger(
            "girlfriend", (daily_rotaiting_handler(logger),),
            level=logger_level)

    workflow_engine = Workflow(
        workflow_list, config, plugin_manager, Context, logger)

    # 获取监听器列表
    listeners = getattr(workflow_module, "listeners", [])
    if isinstance(listeners, types.FunctionType):
        listeners = listeners(workflow_options)
        if not listeners:
            listeners = []

    for listener in listeners:
        workflow_engine.add_listener(listener)

    return workflow_engine


def _get_runtime_args(config, workflow_module, workflow_options, current_env):
    """先获取工作流脚本中的args属性，然后再用env中的args进行更新"""

    # 获取脚本中的args属性
    args = getattr(workflow_module, "args", {})
    if isinstance(args, types.FunctionType):
        args = args(workflow_options)
    if args is None:
        args = {}

    # 获取当前环境中的args属性
    env_args = {} if current_env.args is None else current_env.args
    if isinstance(env_args, types.FunctionType):
        env_args = env_args(workflow_options)
    if env_args is None:
        env_args = {}

    args.update(env_args)
    return args


def _clean_plugins(config):
    # 清理插件
    global plugin_manager, plugin_names
    plugin_manager.sys_cleanup(config, *plugin_names)

if __name__ == "__main__":
    main()

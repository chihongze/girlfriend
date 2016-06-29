# coding: utf-8

"""工作流模板
"""

import argparse
import cmd
import os.path
import re
import types
from abc import ABCMeta, abstractmethod, abstractproperty

import autopep8
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer
from termcolor import colored

import pkg_resources

cmd_parser = argparse.ArgumentParser(description=__doc__.decode("utf-8"))
cmd_parser.add_argument("--file-name", "-f", dest="file_name",
                        default="workflow.py", help=u"工作流文件名称")
cmd_parser.add_argument("--no-highlight", dest="no_highlight",
                        action="store_true", help=u"显示时取消代码高亮")


class CodeTemplate(object):

    __metaclass__ = ABCMeta

    @abstractproperty
    def unit_type(self):
        pass

    @abstractmethod
    def gen_code(self):
        pass

    def __eq__(self, element):
        if isinstance(element, types.StringTypes):
            return element == self.unit_name
        return element.unit_name == self.unit_name


class PluginBasedJobTemplate(CodeTemplate):

    """基于插件的Job模板
    """

    def __init__(self, unit_name, plugin_name=None,
                 auto_imports=None, args_template=None, args_function=None,
                 args_list=None):
        """
        :param unit_name Job名称
        :param plugin_name 插件名称
        :param auto_imports 自动导入列表
        :param args_template 参数模板
        :param args_function 参数函数名称
        """
        self.unit_name = unit_name
        if plugin_name is None:
            self.plugin_name = unit_name
        else:
            self.plugin_name = plugin_name
        self.auto_imports = auto_imports if auto_imports else []
        self.args_template = args_template
        self.args_function = args_function

    @property
    def unit_type(self):
        return "plugin_job"

    def gen_code(self):
        if self.args_template:
            return """
        Job(
            name="{unit_name}",
            plugin="{plugin_name}",
            args={args}
        ),\n""".format(
                unit_name=self.unit_name,
                plugin_name=self.plugin_name,
                args=self.args_template
            )
        elif self.args_function:
            return """
        Job(
            name="{unit_name}",
            plugin="{plugin_name}",
            args={args}
        ),\n""".format(
                unit_name=self.unit_name,
                plugin_name=self.plugin_name,
                args=self.args_function
            )
        else:
            return """
        Job(
            name="{unit_name}",
            plugin="{plugin_name}",
            args={{}}
        ),\n""".format(unit_name=self.unit_name, plugin_name=self.plugin_name)


class CallerBasedJobTemplate(CodeTemplate):

    """基于函数的Job模板
    """

    def __init__(self, unit_name, caller=None):
        """
        :param unit_name Job名称
        :param caller 函数名称，如果为None则为lambda表达式
        """
        self.unit_name = unit_name
        self.caller = caller

    @property
    def unit_type(self):
        return "caller_job"

    def gen_code(self):
        if self.caller is None:
            return """
        Job(
            name="{unit_name}",
            caller=lambda ctx: None,
        ),\n""".format(
                unit_name=self.unit_name,
            )
        else:
            return """
        Job(
            name="{unit_name}",
            caller={caller},
        ),\n""".format(unit_name=self.unit_name, caller=self.caller)


class DecisionTemplate(CodeTemplate):

    """Decision Code Template
    """

    def __init__(self, unit_name, decision_function=None):
        self.unit_name = unit_name
        self.decision_function = decision_function

    @property
    def unit_type(self):
        return "decision"

    def gen_code(self):
        if self.decision_function:
            return """
        Decision(
            "{unit_name}",
            {decision_function}
        ),\n""".format(
                unit_name=self.unit_name,
                decision_function=self.decision_function
            )
        else:
            return """
        Decison(
            {unit_name},
            lambda ctx: None
        ),\n""".format(unit_name=self.unit_name)


class PluginCodeMeta(object):

    def __init__(self, plugin_name, args_template, auto_imports):
        self.plugin_name = plugin_name
        self.args_template = args_template
        self.auto_imports = auto_imports

all_plugin_code_meta = {}


def load_plugin_code_meta():
    # 从entry point加载其它的plugin code meta
    for ep in pkg_resources.iter_entry_points("girlfriend.plugin_code_meta"):
        plugin_code_meta_dict = ep.load()
        all_plugin_code_meta.update(plugin_code_meta_dict)

load_plugin_code_meta()


class WorkflowGenerator(cmd.Cmd):

    def __init__(self, file_name, options):
        cmd.Cmd.__init__(self)
        self.units = []
        self.file_name = file_name
        self.env_list = []  # 运行环境列表
        self.cmd_parser = False
        self.options = options

    def do_plugin_job(self, line):
        """
        添加基于Plugin的Job单元
        :param line 格式：工作单元名称 [插件名称] [参数函数名]
        """
        cmd_args = re.split(r"\s+", line)
        unit_name = cmd_args[0].strip()

        if unit_name in self.units:
            print colored(u"工作单元 '{}' 已经存在".format(unit_name), "red")
            return

        if len(cmd_args) >= 2:
            plugin_name = cmd_args[1].strip()
        else:
            plugin_name = unit_name
        if len(cmd_args) >= 3:
            arg_function = cmd_args[2].strip()
        else:
            arg_function = None

        plugin_code_meta = all_plugin_code_meta.get(plugin_name, None)
        if plugin_code_meta is None:
            plugin_code_meta = PluginCodeMeta(plugin_name, "{}", [])

        if arg_function:
            job_tpl = PluginBasedJobTemplate(
                unit_name, plugin_name, plugin_code_meta.auto_imports,
                None, arg_function)
        else:
            job_tpl = PluginBasedJobTemplate(
                unit_name, plugin_name, plugin_code_meta.auto_imports,
                plugin_code_meta.args_template)
        self.units.append(job_tpl)

    def do_plugin(self, line):
        """
        添加基于Plugin的Job单元
        :param line 格式：工作单元名称 [插件名称] [参数函数名]
        """
        return self.do_plugin_job(line)

    def complete_plugin_job(self, text, line, begin_idx, end_idx):
        """自动完成plugin_job指令
        """
        if not text:
            return all_plugin_code_meta.keys()
        else:
            return [plugin_name for plugin_name in all_plugin_code_meta
                    if plugin_name.startswith(text)]

    def complete_plugin(self, text, line, begin_idx, end_idx):
        """自动完成plugin指令
        """
        self.complete_plugin_job(text, line, begin_idx, end_idx)

    def do_caller_job(self, line):
        """
        添加基于自定义函数的Job单元
        :param line 格式：工作单元名称 [执行函数名]
        """
        cmd_args = re.split(r"\s+", line)
        unit_name = cmd_args[0].strip()

        if unit_name in self.units:
            print colored(u"工作单元 '{}' 已经存在".format(unit_name), "red")
            return

        if len(cmd_args) >= 2:
            func_name = cmd_args[1].strip()
        else:
            func_name = None

        job_tpl = CallerBasedJobTemplate(unit_name, func_name)
        self.units.append(job_tpl)

    def do_caller(self, line):
        """
        添加自定义函数的Job单元
        :param line 格式：工作单元名称 [执行函数名]
        """
        return self.do_caller_job(line)

    def do_decision(self, line):
        """
        添加Decision单元
        :param line 格式：Decision单元名称 [执行函数名]
        """
        if not line:
            print "decison 单元名称 [执行函数名]"
            return
        cmd_args = line.split(" ")
        unit_name = cmd_args[0].strip()
        if len(cmd_args) > 1:
            decision_function = cmd_args[1].strip()
        else:
            decision_function = unit_name
        decision_unit = DecisionTemplate(unit_name, decision_function)
        self.units.append(decision_unit)

    def do_move(self, line):
        """移动某个工作单元
           :param line 格式：目标工作单元 目标位置索引(从0开始)
                            目标工作单元 before 某个工作单元
                            目标工作单元 after 某个工作单元
        """

        if not line:
            print u"move 目标工作单元 目标位置索引(从0开始)"
            print u"move 目标工作单元 before 某个工作单元"
            print u"目标工作单元 after 某个工作单元"
            return

        cmd_parts = re.split(r"\s+", line)
        target_unit = self.units[self.units.index(cmd_parts[0])]

        if target_unit not in self.units:
            print colored(u"目标工作单元'{}'不存在，无法移动".format(target_unit), "red")
            return

        if len(cmd_parts) == 2:
            target_position = int(cmd_parts[1])
            if not (0 <= target_position < len(self.units)):
                print colored(u"目标位置不合法", "red")
                return
            self.units.remove(target_unit)
            self.units.insert(target_position, target_unit)
        elif len(cmd_parts) == 3:
            action = cmd_parts[1]
            sibling_unit = cmd_parts[2]
            if sibling_unit not in self.units:
                print colored(u"参照节点'{}'不存在".format(sibling_unit), "red")
                return

            if action != "before" and action != "after":
                print colored(u"指令格式错误，请参照帮助信息", "red")
                return

            self.units.remove(target_unit)
            if action == "before":
                target_position = self.units.index(sibling_unit)
            elif action == "after":
                target_position = self.units.index(sibling_unit) + 1

            self.units.insert(target_position, target_unit)
        else:
            print colored(u"指令格式错误，请参照帮助信息", "red")
            return

    def do_remove(self, line):
        """
        按照名称，移除某个工作单元
        :param line 工作单元名称
        """
        if line not in self.units:
            print colored(u"找不到工作单元 '{}'".format(line), "red")
            return
        return self.units.remove(line)

    def do_env(self, line):
        """
        添加运行环境
        :param line 运行环境名称
        """
        if line in self.env_list:
            print colored(u"运行环境 '{}' 已经存在".format(line), "red")
            return
        self.env_list.append(line)

    def do_remove_env(self, line):
        """
        移除运行环境
        :param line 运行环境名称
        """
        if line not in self.env_list:
            print colored(u"要移除的运行环境 '{}' 不存在".format(line), "red")
            return
        self.env_list.remove(line)

    def do_cmd_parser(self, line):
        """cmd_parser开关 开启/关闭cmd_parser
        """
        self.cmd_parser = not self.cmd_parser

    def do_show(self, line):
        """Show me the code!
        """
        code = autopep8.fix_code("".join(self._generate_workflow_code()))
        if self.options.no_highlight:
            print code
        else:
            print highlight(code, PythonLexer(), TerminalFormatter())

    def do_clear(self, line):
        """清理已有代码
        """
        line = line.strip()
        if line == "all":
            self.units = []
            self.env_list = []
            self.cmd_parser = False
        elif line == "workflow":
            self.units = []
        elif line == "env":
            self.env_list = []
        else:
            print colored(u"必须指定一个有效的清理目标：all\workflow\env", "red")

    def do_gen(self, line):
        if os.path.exists(self.file_name):
            prompt = u"确定要生成代码？之前的代码文件 '{}' 将被覆盖(y/n)".format(
                self.file_name).encode("utf-8")
            if raw_input(prompt) != 'y':
                return
        with open(self.file_name, "w") as f:
            f.write(autopep8.fix_code("".join(self._generate_workflow_code())))

    def do_EOF(self, line):
        answer = raw_input(u"确定要退出工作流生成器？(y/n)".encode("utf-8"))
        if answer == "y":
            return True
        return False

    def do_exit(self, line):
        """直接退出代码生成器
        """
        exit(0)

    def _generate_workflow_code(self):
        # 记录已经导入的项目
        imported = set()
        generated_functions = set()

        # coding
        yield "# coding: utf-8\n"
        yield "\n"

        # docs
        yield "\"\"\"\n"
        yield "Docs goes here\n"
        yield "\"\"\"\n"
        yield "\n"

        # import elements
        if self.cmd_parser:
            yield "from argparse import ArgumentParser\n"
        yield "from girlfriend.workflow.gfworkflow import Job, Decision\n"
        if self.env_list:
            yield "from girlfriend.workflow.protocol import Env\n"
        for unit in self.units:
            if unit.unit_type != "plugin_job":
                continue
            for import_item in unit.auto_imports:
                if import_item in imported:
                    continue
                imported.add(import_item)
                yield import_item + "\n"
        yield "\n"
        yield "\n"

        # cmd parser
        if self.cmd_parser:
            yield (
                "cmd_parser = ArgumentParser"
                "(description=__doc__.decode(\"utf-8\"))\n"
            )
            yield "cmd_parser.add_argument"
            yield "(\"--option\", \"-o\", dest=\"option\", "
            yield "default=\"\", action=\"store\", help=\"\")\n"
            yield "\n"
            yield "\n"

        # logger
        yield "logger = None\n"
        yield "logger_level = \"info\"\n"
        yield "\n"
        yield "\n"

        # env list
        if self.env_list:
            # env functions
            for env in self.env_list:
                yield "def _{0}_env_args(options):\n".format(env)
                yield "    return {}\n"
                yield "\n\n"
                yield "def _{0}_env_config(options):\n".format(env)
                yield "    return {}\n"
                yield "\n"
            yield "env = (\n"
            for env in self.env_list:
                yield "    Env(\"{0}\", _{0}_env_args, _{0}_env_config),\n"\
                    .format(env)
            yield ")\n"
            yield "\n"

        yield "\n"

        # workflow
        yield "def workflow(options):\n"
        yield "    work_units = (\n"
        for unit in self.units:
            yield "        # {}".format(unit.unit_name)
            yield unit.gen_code()
        yield "\n"
        yield "    )\n"
        yield "\n"
        yield "    return work_units\n"
        yield "\n"

        # args function
        for unit in self.units:

            func = None
            if unit.unit_type == "plugin_job":
                func = getattr(unit, "args_function", None)
            elif unit.unit_type == "caller_job":
                func = getattr(unit, "caller", None)
            elif unit.unit_type == "decision":
                func = getattr(unit, "decision_function", None)

            if func is not None:
                if func in generated_functions:
                    continue
                generated_functions.add(func)
                yield "def {function_name}(context):\n".format(
                    function_name=func)
                if unit.unit_type == "plugin_job":
                    plugin_code_meta = all_plugin_code_meta.get(
                        unit.plugin_name, None)
                    plugin_args = plugin_code_meta.args_template \
                        if plugin_code_meta else None
                    if plugin_args:
                        yield "    return " + plugin_args
                    else:
                        yield "  pass\n"
                else:
                    yield "    pass\n"
                yield "\n"


def gen(path, options):
    WorkflowGenerator(options.file_name, options).cmdloop()

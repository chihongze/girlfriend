# coding: utf-8

"""GirlFriend testing cases，
之所以将test放在girlfriend包下，是为了可以方便将test包也进行安装，
这样围绕girlfriend的第三方项目在开发时也可以复用这些测试工具以及fixtures。
"""

import os
import os.path
import logging
import fixtures
from termcolor import colored
from girlfriend.plugin import plugin_manager as DEFAULT_PLUGIN_MGR
from girlfriend.workflow.gfworkflow import Context
from girlfriend.util.logger import stdout_handler, create_logger


class GirlFriendTestCase(fixtures.TestWithFixtures):

    def color_print(self, msg, color="red"):
        print colored(msg, color)

    def failUnlessException(self, exception_type, logic, *args, **kws):
        """运行指定的函数，如果抛出指定的异常，那么测试通过
           如果没有抛出，那么测试失败。
           :param logic 要测试的可执行对象
           :param args  可执行对象所需要的参数
           :param exception_type 期待抛出的异常
        """
        try:
            logic(*args, **kws)
        except exception_type as e:
            print
            mark = colored("[Exception message] ", "yellow", attrs=['bold'])
            print mark, colored(unicode(e), "yellow")
        else:
            self.fail(
                "Expected exception {} not happened".format(exception_type))

    def assertIsDir(self, file_path):
        """测试文件路径是否是目录类型
        """
        if not os.path.isdir(file_path):
            self.fail(u"The path {} is not a directory".format(file_path))

    def assertFileExist(self, file_path):
        """测试文件路径是否存在
        """
        if not os.path.exists(file_path):
            self.fail(u"The file {} is not existed".format(file_path))

    def assertFileAccess(self, file_path, expected_access):
        """测试文件权限
           :param expected_access 期望的文件权限，接受数字表示，比如八进制0644
        """
        stat = os.stat(file_path)
        file_access = stat.st_mode & 0777
        if file_access != expected_access:
            self.fail((
                "The expected access is {}, "
                "but the file access is {}"
            ).format(oct(expected_access), oct(file_access)))

    def workflow_context(self, config=None, args=None,
                         plugin_mgr=DEFAULT_PLUGIN_MGR, logger=None):
        """构建测试使用的工作流上下文
        """
        config, args = config or {}, args or {}
        if logger is None:
            logger = create_logger(
                "girlfriend", (stdout_handler(),), level=logging.DEBUG)
        return Context(None, config, args, plugin_mgr, logger)

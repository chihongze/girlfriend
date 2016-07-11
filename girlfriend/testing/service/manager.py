# coding: utf-8

import os
import os.path
import zipfile
import shutil
import sqlite3
from girlfriend.testing import GirlFriendTestCase
from girlfriend.service.manager import SQLiteWorkflowManager
from girlfriend.util.sec import md5encode

test_workspace = os.path.join(os.getcwd(), "test_workspace")
db_file = os.path.join(test_workspace, "workflow.db")
workflow_file = """
workflow = [

]
"""


class SQLiteWorkflowManagerTestCase(GirlFriendTestCase):

    def setUp(self):
        global test_workspace
        global workflow_file
        self._wf_mgr = SQLiteWorkflowManager(test_workspace)
        with open("workflow.py", "w+") as f:
            f.write(workflow_file)
        with zipfile.PyZipFile("testwf.zip", mode="w") as f:
            f.write("workflow.py")

    def testPrepareWorkspace(self):
        global test_workspace
        global db_file
        self._wf_mgr.prepare_workspace()
        self.assertTrue(os.path.exists(test_workspace))
        self.assertTrue(os.path.exists(db_file))
        self.assertSQLiteTableExists(db_file, "gf_workflow")

    def testSave(self):
        self._wf_mgr.prepare_workspace()

        # 从无到有进行保存的情况
        with open("testwf.zip", "r") as f:
            file_content = f.read()
            save_rs = self._wf_mgr.save("test", file_content,
                                        "workflow", u"测试工作流")
            self.assertTrue(save_rs.is_ok())
            self.assertEquals(
                save_rs.data.file_hash,
                md5encode(file_content))
            get_rs = self._wf_mgr.get_workflow("test")
            self.assertTrue(get_rs.is_ok())
            self.assertEquals(get_rs.data.code_path, save_rs.data.code_path)
            self.assertEquals(get_rs.data.file_hash, save_rs.data.file_hash)
            self.assertEquals(
                get_rs.data.description, save_rs.data.description)

        # 重复上传同样的代码
        with open("testwf.zip", "r") as f:
            file_content = f.read()
            save_rs = self._wf_mgr.save("test", file_content,
                                        "workflow", u"测试工作流2")
            self.assertTrue(save_rs.is_bad_request())
            self.assertEquals(save_rs.reason, "nothing_changed")

        # name已经存在的情况
        with zipfile.PyZipFile("testwf.zip", mode="w") as f:
            f.writestr("x/__init__.py", "")
            f.writestr("x/a.py", "a = 1\nb = 2")
            f.writestr("x/workflow.py",
                       "import x.a as a\n\ndef x():\n    a.a + a.b")
        with open("testwf.zip", "r") as f:
            file_content = f.read()
            save_rs = self._wf_mgr.save(
                "test", file_content, "x/workflow", u"测试工作流X")
            self.assertTrue(save_rs.is_ok())
            get_rs = self._wf_mgr.get_workflow("test")
            self.assertEquals(get_rs.data.name, save_rs.data.name)
            self.assertEquals(get_rs.data.code_path, save_rs.data.code_path)
            self.assertEquals(get_rs.data.file_hash, save_rs.data.file_hash)
            self.assertEquals(
                get_rs.data.main_module,
                save_rs.data.main_module)

    def testGetWorkflow(self):
        self._wf_mgr.prepare_workspace()

        # 工作流不存在的时候
        rs = self._wf_mgr.get_workflow("test")
        self.assertTrue(rs.is_bad_request())
        self.assertEquals(rs.reason, "workflow_not_exists")

        # 工作流存在的时候
        with open("testwf.zip", "r") as f:
            file_content = f.read()
            self._wf_mgr.save("test", file_content, "workflow", "Workflow")
        rs = self._wf_mgr.get_workflow("test")
        self.assertEquals(rs.data.file_hash, md5encode(file_content))

        # 工作流内容出现了问题
        os.remove(os.path.join(test_workspace, rs.data.code_path))
        rs = self._wf_mgr.get_workflow("test")
        self.assertTrue(rs.is_service_error())
        self.assertEquals(rs.reason, "workflow_file_invalid")

    def testRemove(self):
        self._wf_mgr.prepare_workspace()

        # 工作流不存在的时候
        rs = self._wf_mgr.remove("test")
        self.assertTrue(rs.is_bad_request())

        # 工作流已经存在的时候
        with open("testwf.zip", "r") as f:
            file_content = f.read()
            save_rs = self._wf_mgr.save(
                "test", file_content, "workflow", u"Workflow")
        rs = self._wf_mgr.remove("test")
        self.assertTrue(rs.is_ok())
        self.assertFalse(os.path.exists(
            os.path.join(test_workspace, save_rs.data.code_path)))
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "select id from gf_workflow where name = ?", ("test",))
            row = cursor.fetchone()
            self.assertIsNone(row)

    def tearDown(self):
        global test_workspace
        if os.path.exists(test_workspace):
            shutil.rmtree(test_workspace)
        if os.path.exists("workflow.py"):
            os.remove("workflow.py")
        if os.path.exists("testwf.zip"):
            os.remove("testwf.zip")

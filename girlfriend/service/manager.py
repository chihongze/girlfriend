# coding: utf-8

"""该模块用于提供工作流的管理，包括工作流的上传存储、
   移除工作流、查看工作流详情等。
"""

import sys
import time
import sqlite3
import os.path
import random
import datetime
import zipimport
from abc import ABCMeta, abstractmethod
from girlfriend.service.model import (
    Result,
    WorkflowInfo
)
from girlfriend.util.sec import md5encode
from girlfriend.util.logger import GF_LOG


class WorkflowManager(object):

    """提供工作流对象信息的各种增删改查操作
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def get_workflow(self, workflow_name):
        """根据名称获取某个工作流的信息
           :param workflow_name 工作流的名称
           :return Result对象
                {
                    code: 200,
                    data: {
                        name: xxx,
                        code_path: xxx,
                        updated_on: xxxx-xx-xx xx:xx:xx,
                        created_on: xxxx-xx-xx xx:xx:xx
                    }
                }
        """
        pass

    @abstractmethod
    def get_all(self):
        """获取所有的工作流信息
           :return Result对象
                {
                    code: 200,
                    data: [
                        {workflow1},
                        {workflow2},
                        {workflow3},
                    ]
                }
        """
        pass

    @abstractmethod
    def save(self, name, code_content, main_module, description):
        """根据名称来保存工作流到工作目录
           如果工作流不存在，那么会创建新的记录，
           如果已经存在，则实施替换，替换之前会对之前的工作流文件做备份
           :param name 工作流名称
           :param code_content 工作流文件bytes格式内容
           :param description 工作流描述
           :return Result {
                code: 200,
                message: success
           }
        """
        pass

    @abstractmethod
    def remove(self, workflow_name):
        """根据名称来移除某个工作流
           :param workflow_name 工作流名称
        """
        pass


class SQLiteWorkflowManager(WorkflowManager):

    """基于SQLite的WorkflowManager实现
    """

    _SQL_CREATE_WORKFLOW_TABLE = (
        "create table if not exists gf_workflow ("
        "  id integer primary key autoincrement not null,"
        "  name varchar(20) unique not null,"
        "  code_path text not null,"
        "  main_module text not null,"
        "  description text not null,"
        "  file_hash character(32) not null,"
        "  updated_on integer not null,"
        "  created_on integer not null"
        ")"
    )

    def __init__(self, work_dir):
        self._work_dir = work_dir
        self._db_file = os.path.join(work_dir, "workflow.db")

    def prepare_workspace(self):
        """初始化工作目录，如果目录不存在，则将目录建立起来
           如果数据库不存在，则将数据库和相关的表建立起来
           如果都存在，则什么都不做。
        """

        # 创建工作目录
        if not os.path.exists(self._work_dir):
            os.mkdir(self._work_dir)

        # 连接数据库文件，如果数据库文件不存在，会自动创建
        with sqlite3.connect(self._db_file) as db_conn:
            db_conn.executescript(
                SQLiteWorkflowManager._SQL_CREATE_WORKFLOW_TABLE)

    def get_workflow(self, workflow_name):
        workflow = self._get_by_name(workflow_name)
        if workflow is None:  # 目标工作流不存在
            return Result.bad_request(
                reason="workflow_not_exists",
                message=u"工作流 '{}' 不存在".format(workflow_name)
            )

        workflow_file = os.path.join(self._work_dir, workflow.code_path)
        if not os.path.exists(workflow_file):
            return Result.service_error(
                reason="workflow_file_invalid",
                message=u"找不到可执行的工作流文件"
            )

        # 安全返回工作流对象
        return Result.ok(data=workflow)

    def get_all(self):
        with sqlite3.connect(self._db_file) as conn:
            cursor = conn.cursor()
            cursor.execute((
                "select name, code_path, main_module, "
                "description, file_hash, updated_on, created_on "
                "from gf_workflow"
            ))
            rows = cursor.fetchmany()
            if not rows:
                return []
            return [self._build_record_from_db_row(row) for row in rows]

    def save(self, name, code_content, main_module, description):
        """
        S0. 判断工作流是否存在，如果存在，则对比文件的md5 hash，hash一致什么都不用做了。
        S1. 如果工作流存在，查看当前工作流任务处理情况，如果有任务，立即返回
        S2. 判断工作流文件格式，看能否成功导出模块，如果无法导出模块，则返回错误
        S3. 如果工作流已经存在，那么执行替换操作。
        S4. 如果工作流不存在，则添加新记录。
        """
        code_content_md5 = md5encode(code_content)
        rs = self.get_workflow(name)
        if rs.is_ok():
            existed_wf = rs.data
            if code_content_md5 == existed_wf.file_hash:
                return Result.bad_request(
                    reason="nothing_changed",
                    message=u"此工作流已经存在")

        # TODO 查看任务处理情况

        # 将工作流代码写入新文件
        new_file_name = self._gen_wf_file_name(name, code_content_md5)
        new_file_path = os.path.join(self._work_dir, new_file_name)
        with open(new_file_path, "w") as f:
            f.write(code_content)

        # 测试是否可以正常加载main module
        try:
            sys.path.append(new_file_path)
            zipimport.zipimporter(new_file_path).load_module(main_module)
        except zipimport.ZipImportError as e:
            os.remove(new_file_path)
            GF_LOG.exception(e)
            return Result.bad_request(
                reason="load_module_error", message=unicode(e))
        except Exception as e:
            os.remove(new_file_path)
            GF_LOG.exception(e)
            return Result.bad_request(reason="load_module_error",
                                      message=unicode(e))
        finally:
            sys.path.remove(new_file_path)

        now_timestamp = int(time.time())
        now = datetime.datetime.fromtimestamp(now_timestamp)

        if rs.is_ok():
            with sqlite3.connect(self._db_file) as conn:
                cursor = conn.cursor()
                cursor.execute((
                    "update gf_workflow set code_path = ?, main_module = ?, "
                    "description = ?, file_hash = ?, updated_on = ? "
                    "where name = ?"
                ), (new_file_name, main_module, description, code_content_md5,
                    now_timestamp, name))
                conn.commit()
                # 将旧的文件删掉
                os.remove(os.path.join(self._work_dir, rs.data.code_path))
        else:
            with sqlite3.connect(self._db_file) as conn:
                cursor = conn.cursor()
                cursor.execute((
                    "insert into gf_workflow "
                    "(name, code_path, main_module, description, file_hash, "
                    "updated_on, created_on) values ("
                    "?, ?, ?, ?, ?, ?, ?)"
                ), (name, new_file_name, main_module, description,
                    code_content_md5, now_timestamp, now_timestamp))

        return Result.ok(data=WorkflowInfo(
            name=name,
            code_path=new_file_name,
            main_module=main_module,
            description=description,
            file_hash=code_content_md5,
            updated_on=now,
            created_on=now))

    def _gen_wf_file_name(self, name, code_content_hash):
        _hash = md5encode((
            "{name}"
            "{code_content_hash}"
            "{time}"
            "{random}"
        ).format(
            name=name,
            code_content_hash=code_content_hash,
            time=int(time.time()),
            random=random.randint(0, 100000)
        ))
        return _hash + ".zip"

    def remove(self, workflow_name):
        workflow = self._get_by_name(workflow_name)

        # 找不到对象！
        if not workflow:
            return Result.bad_request(
                reason="workflow_not_exists",
                message=u"找不到工作流对象"
            )

        # 先删文件
        full_file_path = os.path.join(self._work_dir, workflow.code_path)
        if os.path.exists(full_file_path):
            os.remove(full_file_path)

        with sqlite3.connect(self._db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "delete from gf_workflow where name = ?", (workflow_name,))

        return Result.ok(data=workflow)

    def _get_by_name(self, name):
        with sqlite3.connect(self._db_file) as conn:
            cursor = conn.cursor()
            cursor.execute((
                "select name, code_path, main_module, description, file_hash, "
                "updated_on, created_on "
                "from gf_workflow where name = ?"
            ), (name, ))
            row = cursor.fetchone()
            if not row:
                return None
            return self._build_record_from_db_row(row)

    def _build_record_from_db_row(self, row):
        return WorkflowInfo(
            name=row[0],
            code_path=row[1],
            main_module=row[2],
            description=row[3],
            file_hash=row[4],
            updated_on=datetime.datetime.fromtimestamp(row[5]),
            created_on=datetime.datetime.fromtimestamp(row[6])
        )

# coding: utf-8

import types
import codecs
import os.path
from girlfriend.exception import InvalidArgumentException
from girlfriend.util.lang import args2fields


class ReadTextPlugin(object):

    name = "read_text"

    def execute(self, context, *readers):
        return [reader(context) for reader in readers]


class TextR(object):

    """读取处理单个文件
    """

    @args2fields()
    def __init__(self, filepath, record_matcher="line",
                 record_handler=None, record_filter=None,
                 pointer=None, change_file_logic=None,
                 max_line=None, result_wrapper=None, variable=None):
        """
        :param filepath: 要读取的文件路径
        :param record_matcher: 记录匹配器
        :param record_handler: 记录处理器
        :param record_filter: 记录过滤器
        :param pointer: 指针文件
        :param change_file_logic: 文件切换逻辑
        :param max_line: 一次处理的最大行数
        :param result_wrapper: 结果包装器
        :param variable: 存储变量名
        """
        pass

    class TextRecordContext(object):

        def __init__(self, filepath, pos, record_matcher,
                     record_handler, record_filter, pointer,
                     max_line, records):
            self.filepath = filepath
            self.current_pos = pos
            self.record_pos = pos
            self.record_matcher = record_matcher
            self.record_handler = record_handler
            self.record_filter = record_filter
            self.max_line = max_line
            self.records = records
            self.pointer = pointer
            self.record_buffer = []
            self.current_line = None

        @property
        def buffer_size(self):
            return len(self.record_buffer)

        def read(self):
            with codecs.open(self.filepath, "r", "utf-8") as f:
                f.seek(self.current_pos)  # 定位到指定位置
                for num, line in enumerate(f, start=1):
                    if self.max_line and num > self.max_line:
                        break
                    self.current_line = line.strip()
                    self.current_pos += len(line.encode("utf-8"))
                    self.record_matcher(self)
                self.save_pointer()
                return self.records

        def add(self, obj=None):
            # 添加记录到缓冲
            if obj is None:
                obj = self.current_line
            self.record_buffer.append(obj)

        def end(self):
            if self.record_filter is None or \
                    self.record_filter(self.record_buffer):
                if self.record_handler is None:
                    self.records.append(self.record_buffer)
                else:
                    self.records.append(
                        self.record_handler(self.record_buffer))
            # 清空buffer
            self.record_buffer = []
            # 修改记录位置
            self.record_pos = self.current_pos

        def prepare_read(self, until):
            with codecs.open(self.filepath, "r", "utf-8") as f:
                f.seek(self.current_pos)
                lines = []
                for line in f:
                    if not until(line):
                        break
                    lines.append(line)
                return lines

        def save_pointer(self):
            if not self.pointer:
                return
            with open(self.pointer, "w") as f:
                f.write("{}\n{}".format(
                    self.record_pos, os.stat(self.filepath).st_ino))

    def __call__(self, context):
        read_file_queue = self._get_read_file_queue(context)
        result = []
        for read_file_info in read_file_queue:
            filepath, pos = read_file_info
            record_matcher = self._record_matcher
            if isinstance(self._record_matcher, types.StringTypes):
                if self._record_matcher == "line":
                    def record_matcher(ctx):
                        if ctx.record_filter is None or \
                                ctx.record_filter(ctx.current_line):
                            if ctx.record_handler is None:
                                ctx.records.append(ctx.current_line)
                            else:
                                ctx.records.append(
                                    ctx.record_handler(ctx.current_line))
                            ctx.record_pos = ctx.current_pos
                else:
                    raise InvalidArgumentException(
                        u"record_matcher参数的值必须是函数或者是\"line\"")
            TextR.TextRecordContext(
                filepath=filepath,
                pos=pos,
                record_matcher=record_matcher,
                record_handler=self._record_handler,
                record_filter=self._record_filter,
                pointer=self._pointer,
                max_line=self._max_line,
                records=result
            ).read()

        if self._result_wrapper is not None:
            result = self._result_wrapper(result)

        if self._variable:
            context[self._variable] = result

        return result

    def _get_read_file_queue(self, context):
        if not os.path.exists(self._filepath):
            raise InvalidArgumentException(
                u"目标文件 '{}' 不存在".format(self._filepath))
        read_file_queue = []
        if self._pointer is None or not os.path.exists(self._pointer):
            read_file_queue.append((self._filepath, 0))
            return read_file_queue
        saved_pos, saved_inode = self._read_pointer()
        # 比较inode是否一致
        if os.stat(self._filepath).st_ino == saved_inode:
            read_file_queue.append((self._filepath, saved_pos))
        else:
            if self._change_file_logic is None:
                raise InvalidArgumentException(
                    u"文件已经切换，但是未指定change_file_logic文件切换逻辑")
            old_file = self._change_file_logic(context)
            read_file_queue.append((old_file, saved_pos))
            read_file_queue.append((self._filepath, 0))
        return read_file_queue

    def _read_pointer(self):
        with open(self._pointer, "r") as f:
            records = [line.strip() for line in f]
            return int(records[0]), int(records[1])

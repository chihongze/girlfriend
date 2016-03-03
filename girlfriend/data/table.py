# coding: utf-8

"""本模块包含Table数据结构的抽象以及一个基于二维列表的Table实现，
很多以表格为核心的插件比如excel都会依赖Table结构。
"""

import types
import prettytable
from abc import (
    ABCMeta,
    abstractproperty,
    abstractmethod
)
from girlfriend.exception import InvalidTypeException
from girlfriend.data.exception import (
    IndexOutOfBoundsException,
    MissingKeyException,
    InvalidSizeException
)
from girlfriend.util.lang import SequenceCollectionType


class AbstractTable(object):

    """抽象的Table接口
       在构建新的Table结构和依赖Table的插件时,应尽量依赖于此约定展开工作
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractproperty
    def name(self):
        """表格的名称
        """
        pass

    @abstractproperty
    def titles(self):
        """以可迭代对象的形式返回表格的列名
        """
        pass

    @abstractproperty
    def row_num(self):
        """表格行数
        """
        pass

    @abstractproperty
    def column_num(self):
        """表格列数
        """
        pass

    def __len__(self):
        """表格的长度默认为行数
        """
        return self.row_num

    @abstractmethod
    def row(self, index):
        """获取某一行
        """
        pass

    @abstractmethod
    def __getitem__(self, index):
        """根据索引获取某一行
        """
        pass

    @abstractmethod
    def append(self, row):
        """添加行
        """
        pass

    @abstractmethod
    def __iter__(self):
        pass


class Title(object):

    """表格标题"""

    def __init__(self, name, title=None):
        """
        :param name: 标题名,可以方便用来进行变量引用,比如id、age、grade等等
        :param title: 供显示的标题名,比如编号/年龄/等级,可以不指定,默认为name的值
        """
        self._name = name
        if title is None:
            self._title = name
        else:
            self._title = title

    @property
    def name(self):
        return self._name

    @property
    def title(self):
        return self._title

    def __repr__(self):
        return self._title

    def __str__(self):
        return self._title


class Row(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def __getattr__(self, key):
        pass

    @abstractmethod
    def __getitem__(self, key):
        pass

    @abstractmethod
    def __len__(self):
        pass

    @abstractmethod
    def __iter__(self, key):
        pass


class BaseLocalTable(AbstractTable):

    """基于本地对象的Table实现
    """

    __metaclass__ = ABCMeta

    def __init__(self, name, titles, data, row_type):
        self._name = name
        self._titles = titles
        if data is None:
            self._data = []
        else:
            self._data = data
        self._row_type = row_type
        self._mapping = self._gen_mapping()

    @abstractmethod
    def _gen_mapping(self):
        pass

    @property
    def name(self):
        return self._name

    @property
    def titles(self):
        return self._titles

    @property
    def row_num(self):
        return len(self._data)

    @property
    def column_num(self):
        return len(self._titles)

    def row(self, row_index):
        self._check_row_index(row_index)
        return self._row_type(self._data[row_index], self._mapping)

    def __getitem__(self, row_index):
        return self.row(row_index)

    def _check_row_index(self, row_index):
        if row_index >= self.row_num:
            raise IndexOutOfBoundsException(
                u"row_index={0}超出了边界，row_num={1}".format(
                    row_index,
                    self.row_num
                ))

    def _check_col_index(self, column_index):
        if column_index >= self.column_num:
            raise IndexOutOfBoundsException(
                u"column_index={0}，column_num={1}".format(
                    column_index,
                    self.column_num
                ))

    def __iter__(self):
        for row in self._data:
            yield self._row_type(row, self._mapping)

    def __str__(self):
        ptable = prettytable.PrettyTable(title.title for title in self.titles)
        for row in self:
            ptable.add_row(row)
        return str(ptable)


class BaseLocalRow(Row):

    __metaclass__ = ABCMeta

    def __init__(self, row_object, mapping):
        self._row = row_object
        self._mapping = mapping

    @property
    def obj(self):
        """返回被包装的对象"""
        return self._row

    @abstractmethod
    def __getitem__(self, index):
        pass

    @abstractmethod
    def __getattr__(self, attr_name):
        pass

    def __len__(self):
        return len(self._mapping)

    def __iter__(self):
        return iter(self._row)

    def __repr__(self):
        return repr(self._row)

    def __str__(self):
        return str(self._row)


class TableWrapper(object):

    """表格包装器，能够根据列表中元素的类型，自动选择对应的表格类型进行包装
    """

    def __init__(self, name, titles, table_type=None, auto_title_name=False):
        self._name = name
        self._titles = self._handle_titles(titles, auto_title_name)
        self._table_type = table_type

    def __call__(self, data):
        table_type = self._get_table_type(data)
        return table_type(
            name=self._name,
            titles=self._titles,
            data=data
        )

    def _handle_titles(self, titles, auto_title_name):
        """对Title进行处理，接受两种形式的title
           接受纯Title对象的列表或者元组，例如:
           (Title("id", u"编号"), Title("name", u"姓名"), Title("grade", u"年级"))
           也接受字符串描述的元组:
           ("id", u"编号", "name", u"姓名", "grade", u"年级")
        """
        first_ele = titles[0]
        if isinstance(first_ele, Title):
            return titles
        elif isinstance(first_ele, types.StringTypes):
            if auto_title_name:
                return [Title("field_%d" % idx, arg)
                        for idx, arg in enumerate(titles)]
            else:
                return [Title(*arg) for arg in zip(titles[::2], titles[1::2])]
        else:
            raise InvalidTypeException(u"title列表元素只允许字符串和Title类型")

    def _get_table_type(self, data):
        # 自动推断应该使用的table类型
        if self._table_type is not None:
            return self._table_type

        # 空列表
        if data is None or len(data) == 0:
            return ListTable

        # 默认取第一行进行推断
        row = data[0]
        if isinstance(row, SequenceCollectionType):
            return ListTable
        elif isinstance(row, types.DictType):
            return DictTable
        else:
            return ObjectTable


class ListTable(BaseLocalTable):

    """基于二维list的Table实现
    """

    def __init__(self, name, titles, data=None):
        """
        :param name: 表格名称
        :param titles: 表格标题
        :param data: 如果data为None，那么会生成一个新的二维列表
                    如果不为None，那么包装既有的二维列表
        """
        BaseLocalTable.__init__(self, name, titles, data, ListRow)

    def _gen_mapping(self):
        return {title.name: idx for idx, title in enumerate(self.titles)}

    def cell(self, row_index, column_index):
        self._check_row_index(row_index)
        self._check_col_index(column_index)
        return self._data[row_index][column_index]

    def append(self, row):
        """添加新的一行
        """
        if not isinstance(row, SequenceCollectionType):
            raise InvalidTypeException(u"新行的类型必须是list或者tuple类型")
        if len(row) > self.column_num:
            raise InvalidSizeException(
                u"新行的列数为{0}，表格的列数为{1}，两者不一致".format(
                    len(row),
                    self.column_num
                ))
        self._data.append(row)


class ListRow(BaseLocalRow):

    """基于List/Tuple实现的行对象
    """

    def __init__(self, row_list, mapping):
        BaseLocalRow.__init__(self, row_list, mapping)

    def __getitem__(self, key):
        if isinstance(key, (types.IntType, types.LongType)):
            return self._row[key]
        elif isinstance(key, (types.StringType)):
            index = self._mapping.get(key, None)
            if index is None:
                raise MissingKeyException(
                    u"找不到与key={}相关联的值".format(key))
            return self._row[index]
        elif isinstance(key, SequenceCollectionType):
            index_list = (self._mapping.get(k) for k in key)
            return tuple(self._row[index] for index in index_list)
        else:
            raise InvalidTypeException(
                u"不合法的key类型：{}".format(type(key).__name__))

    def __getattr__(self, key):
        index = self._mapping.get(key, None)
        if index is None:
            raise AttributeError(u"找不到属性{}".format(key))
        return self._row[index]


class ObjectTable(BaseLocalTable):

    """ObjectTable中的每一行都是一个具体的对象
    """

    def __init__(self, name, titles, data=None):
        BaseLocalTable.__init__(self, name, titles, data, ObjectRow)

    def _gen_mapping(self):
        return [title.name for title in self.titles]

    def cell(self, row_index, column_index):
        self._check_row_index(row_index)
        self._check_col_index(column_index)
        obj = self._data[row_index]
        attr_name = self._mapping[row_index]
        return getattr(obj, attr_name)

    def append(self, row):
        self._data.append(row)


class ObjectRow(BaseLocalRow):

    def __init__(self, row_obj, mapping):
        BaseLocalRow.__init__(self, row_obj, mapping)

    def __getitem__(self, key):
        if isinstance(key, types.StringTypes):
            return getattr(self._row, key)
        if isinstance(key, (types.IntType, types.LongType)):
            key = self._mapping[key]
            return getattr(self._row, key)
        if isinstance(key, SequenceCollectionType):
            return tuple(getattr(self._row, k) for k in key)

    def __getattr__(self, key):
        return getattr(self._row, key)

    def __iter__(self):
        for i in xrange(0, len(self._mapping)):
            yield getattr(self._row, self._mapping[i])


class DictTable(BaseLocalTable):

    """DictTable的每一行都是一个字典对象
    """

    def __init__(self, name, titles, data=None):
        BaseLocalTable.__init__(self, name, titles, data, DictRow)

    def _gen_mapping(self):
        return [title.name for title in self._titles]

    def cell(self, row_index, column_index):
        self._check_row_index(row_index)
        self._check_col_index(column_index)
        row = self._data[row_index]
        key = self._mapping(column_index)
        return row[key]

    def append(self, row):
        if not isinstance(row, types.DictType):
            raise InvalidTypeException(u"DictTable只能接受字典类型的行对象")
        if len(row) != self.column_num:
            raise InvalidSizeException(
                u"新行的列数为{0}，表格的列数为{1}，两者不一致".format(len(row), self.column_num)
            )
        self._data.append(row)


class DictRow(BaseLocalRow):

    def __init__(self, row_obj, mapping):
        BaseLocalRow.__init__(self, row_obj, mapping)

    def __getitem__(self, key):
        if isinstance(key, types.StringTypes):
            return self._row[key]
        if isinstance(key, (types.IntType, types.LongType)):
            key = self._mapping[key]
            return self._row[key]
        if isinstance(key, SequenceCollectionType):
            return tuple(self._row[k] for k in key)

    def __getattr__(self, key):
        return self._row[key]

    def __iter__(self):
        for i in xrange(len(self._mapping)):
            yield self._row[self._mapping[i]]

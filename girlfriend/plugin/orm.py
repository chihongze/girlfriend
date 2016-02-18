# coding: utf-8

"""基于SQLAlchemy的ORM插件
"""

import re
import ujson
import types
import threading
import collections
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.query import Query as ORMQuery
from sqlalchemy.pool import Pool, QueuePool, NullPool
from sqlalchemy.ext.automap import automap_base
from girlfriend.exception import InvalidStatusException
from girlfriend.util.validating import Rule, be_json
from girlfriend.util.lang import (
    args2fields,
    SequenceCollectionType,
    parse_context_var
)


class EngineManager(object):

    """通过EngineManager来管理所有的Engine对象
       这样所有的SQLAlchemy插件就可以实现Engine共享
    """

    STATUS_UNINIT = 0  # 尚未初始化

    STATUS_OK = 1  # 状态OK

    STATUS_DISPOSED = 2  # 已经销毁

    # 数据源配置项的验证规则
    config_rules = (
        # 连接字符串，比如postgresql://scott:tiger@localhost/test
        Rule("connect_url", required=True,
             type=types.StringTypes, regex=r"^\w+://"),
        # 编码
        Rule("encoding", required=False,
             type=types.StringTypes, default="utf-8"),
        # 连接参数，采用json的形式:{'ssl': {'cert': xxx, 'key': xxx, 'ca': xxx}}
        Rule("connect_args", required=False,
             type=types.StringTypes, default="{}",
             logic=be_json("connect_args")),
        # 该数据源使用的连接池策略
        Rule("pool_policy", required=False,
             type=types.StringTypes, default=None)
    )

    # 连接池的配置项验证规则，section名称皆以dbpool_开头
    pool_config_rules = (
        # 连接池类型，比如sqlalchemy.pool.QueuePool，可以是字符串，也可以是具体的类对象
        Rule("poolclass", required=True, type=(Pool, types.StringTypes)),
        # 连接池大小
        Rule("pool_size", required=False, type=(int, types.StringTypes),
             regex=r"^\d+$", default=10),
        # 连接回收周期，单位为秒，MySQL尤其要注意设置此项，否则连接会自动过期断开
        Rule("pool_recycle", required=False, type=(int,),
             regex=r"^\d+$", default=3600),
        # 从连接池中获取连接的超时时间，SQLAlchemy自带连接池中，只能用于QueuePool
        Rule("pool_timeout", required=False, type=(
            int,), regex=r"^\d+$", default=30),
    )

    def __init__(self):
        self._engines = {}
        self._status = EngineManager.STATUS_UNINIT
        self._validated = False

    def validate_config(self, config):
        """统一对配置进行验证，避免各个插件单独验证
        """
        if self._validated:
            return
        for section in config.prefix("db_", "dbpool_"):
            if section.startswith("db_"):
                self._validate_config_items(
                    config, section, EngineManager.config_rules)
            elif section.startswith("dbpool_"):
                self._validate_config_items(
                    config, section, EngineManager.pool_config_rules)

        self._validated = True

    def _validate_config_items(self, config, section, rules):
        config_items = config[section]
        for rule in rules:
            item_value = config_items.get(rule.name)
            rule.validate(item_value)
            if item_value is None and not rule.required:
                config[section][rule.name] = rule.default

    def init_all(self, config):
        """统一初始化
        """
        if self._status != EngineManager.STATUS_UNINIT:
            return
        all_pool_config = self._load_db_pool_config(config)
        for section in config.prefix("db_"):
            engine_name = section.split("_", 1)[1]
            engine = self._create_engine(config, section, all_pool_config)
            self._engines[engine_name] = EngineContainer(engine)
        self._status = EngineManager.STATUS_OK

    def _load_db_pool_config(self, config):
        """对连接池进行初始化
        """
        pool_config = {}
        for section in config.prefix("dbpool_"):
            pool_name = section.split("_", 1)[1]
            pool_config[pool_name] = config[section]

            # 对字符串的配置项做一点微小的工作
            poolclass = pool_config[pool_name]["poolclass"]
            if isinstance(poolclass, str):
                if poolclass.lower() == "queuepool":
                    poolclass = QueuePool
                elif poolclass.lower() == "nullpool":
                    poolclass = NullPool
                else:
                    module_name, class_name = poolclass.rsplit(".", 1)
                    poolclass = getattr(__import__(module_name), class_name)
                pool_config[pool_name]["poolclass"] = poolclass

            for item_name in ("pool_size", "pool_recycle", "pool_timeout"):
                item_value = pool_config[pool_name][item_name]
                pool_config[pool_name][item_name] = int(item_value)
        return pool_config

    def _create_engine(self, config, section, all_pool_config):
        config_items = config[section]
        pool_policy = config[section]["pool_policy"]
        kws = {}
        if pool_policy is not None:
            pool_config = all_pool_config[pool_policy]
            if pool_config["poolclass"] != NullPool:
                kws = pool_config
        return create_engine(
            config_items["connect_url"],
            encoding=config_items["encoding"],
            connect_args=ujson.loads(config_items["connect_args"]),
            ** kws
        )

    def engine(self, engine_name):
        """根据引擎名字来获取引擎
        """
        if self._status != EngineManager.STATUS_OK:
            raise InvalidStatusException(u"Engine尚未初始化")
        return self._engines[engine_name]

    def dispose_all(self):
        """统一对引擎进行销毁
        """
        if self._status != EngineManager.STATUS_OK:
            return
        for _, engine_container in self._engines.items():
            engine_container.engine.dispose()
        self._status = EngineManager.STATUS_DISPOSED

_engine_manager = EngineManager()


class EngineContainer(object):

    """存储engine对象，并封装/代理一些与engine对象有关的操作
    """

    def __init__(self, engine):
        self.engine = engine
        self.sessionmaker = sessionmaker(bind=engine)
        self._base_model_class = None
        self._base_model_class_sem = threading.Lock()

    def session(self):
        return self.sessionmaker()

    @property
    def base_model_class(self):
        if self._base_model_class is not None:
            return self._base_model_class
        # 并发环境下，防止重复初始化
        with self._base_model_class_sem:
            # 虽然已经获得了锁，但是先人已经初始化了，立即返回
            if self._base_model_class is not None:
                return self._base_model_class
            self._base_model_class = automap_base()
            self._base_model_class.prepare(self.engine, reflect=True)
            return self._base_model_class


class OrmQueryPlugin(object):

    name = "orm_query"

    @staticmethod
    def config_validator(config):
        """配置验证器
        """
        global _engine_manager
        _engine_manager.validate_config(config)

    def __init__(self):
        self._engines = {}

    def sys_prepare(self, config):
        global _engine_manager
        _engine_manager.init_all(config)

    def execute(self, context, *exec_list):
        # 按顺序执行exec_list
        return [exec_(context) for exec_ in exec_list]

    def sys_cleanup(self, config):
        global _engine_manager
        _engine_manager.dispose_all()

_SELECT_STATEMENT_REGEX = re.compile("^select ", re.IGNORECASE)


class Query(object):

    """描述ORM查询信息以及执行查询操作
    """

    @args2fields()
    def __init__(self, engine_name, variable_name,
                 query_items, query=None, order_by=None, group_by=None,
                 params=None, row_handler=None, result_wrapper=None):
        """
        :param engine_name   使用的引擎名称
        :param variable_name 查询的结果将以此为变量名写入context
        :param query_items   查询项目，可以指定class类型和字符串类型
                             如果是字符串类型，那么会启用auto map进行处理
        :param query         接受回调函数或者是SQL以及字符串描述的查询条件
        :param params        如果基于文本或者SQL查询，那么可以通过此字段来传递参数
        :param row_handler   行处理器，针对每一行做格式转换操作
        :param result_wrapper 用于对查询结果进行包装，比如将查询结果包装成table对象
        """
        if isinstance(order_by, str):
            self._order_by = text(order_by)

    def __call__(self, context):
        global _engine_manager
        engine = _engine_manager.engine(self._engine_name)

        # 处理查询项
        query_items = []
        if isinstance(self._query_items, types.StringTypes):
            query_items.append(self.automap(engine, self._query_items))
        elif isinstance(self._query_items, collections.Iterable):
            for query_item in self._query_items:
                if isinstance(query_item, types.StringTypes):
                    query_item = self.automap(engine, query_item)
                query_items.append(query_item)
        else:
            query_items.append(self._query_items)

        # 解析params中的context变量
        if self._params:
            self._params = {
                key: parse_context_var(context, self._params[key])
                for key in self._params}

        session = engine.session()
        try:
            query = None
            if isinstance(self._query, types.StringTypes):
                if _SELECT_STATEMENT_REGEX.search(self._query):
                    if self._params is None:
                        self._params = {}
                    query = session.query(*query_items).from_statement(
                        text(self._query)).params(**self._params)
                else:
                    query = self._build_query(engine, session, query_items)
            elif isinstance(self._query, types.FunctionType):
                result = self._query(session, context, *query_items)
                # 可以返回查询对象，也可以返回查询结果
                if isinstance(result, ORMQuery):
                    query = result
                else:
                    if self._row_handler:
                        result = tuple(self._row_handler(row)
                                       for row in result)
                    if self._result_wrapper is not None:
                        result = self._result_wrapper(result)
                    context[self._variable_name] = result
                    return result
            else:
                query = self._build_query(engine, session, query_items)

            result = self._build_result(query)
            context[self._variable_name] = result
            return result
        finally:
            session.close()

    def automap(self, engine, query_item_str):
        base = engine.base_model_class
        if "." in query_item_str:
            table_name, field_name = query_item_str.split(".", 1)
            clazz = getattr(base.classes, table_name, None)
            return getattr(clazz, field_name, None)
        else:
            return getattr(base.classes, query_item_str, None)

    def _build_query(self, engine, session, query_items):
        query = session.query(*query_items)
        if self._query is not None:
            if isinstance(self._query, types.StringTypes):
                query = query.filter(text(self._query))
            else:
                query = query.filter(self._query)
        if self._order_by is not None:
            query = query.order_by(self._order_by)
        if self._group_by is not None:
            if isinstance(self._group_by, types.StringTypes):
                self._group_by = self.automap(engine, self._group_by)
            query = query.group_by(self._group_by)
        if self._params is not None:
            query = query.params(**self._params)
        return query

    def _build_result(self, query):
        if self._row_handler:
            result = tuple(self._row_handler(row) for row in query)
        else:
            result = query.all()
        if self._result_wrapper is not None:
            return self._result_wrapper(result)
        return result


class SQL(object):

    """使用该对象可以直接描述非ORM的SQL查询
    """

    @args2fields()
    def __init__(self, engine_name, variable_name, sql, params=None,
                 row_handler=None, result_wrapper=None):
        if params is None:
            self._params = {}

    def __call__(self, context):
        global _engine_manager

        engine_container = _engine_manager.engine(self._engine_name)
        session = engine_container.session()
        if isinstance(self._sql, types.StringTypes) and \
                _SELECT_STATEMENT_REGEX.search(self._sql):
            return self._execute_select_statement(session, context)
        else:
            # 非查询语句
            try:
                if isinstance(self._sql, types.StringTypes):
                    session.execute(self._sql, self._params)
                # 批量执行
                elif isinstance(self._sql, SequenceCollectionType):
                    if isinstance(self._params, SequenceCollectionType):
                        for idx, sql in enumerate(self._sql):
                            session.execute(sql, self._params[idx])
                    else:
                        for sql in self._sql:
                            session.execute(sql)
                session.commit()
            finally:
                session.close()

    def _execute_select_statement(self, session, context):
        try:
            result_proxy = session.execute(self._sql, self._params)
            result = None
            if self._row_handler is not None:
                result = tuple(self._row_handler(row) for row in result_proxy)
            else:
                result = tuple(tuple(row) for row in result_proxy)
            if self._result_wrapper is not None:
                result = self._result_wrapper(result)
            context[self._variable_name] = result
            result_proxy.close()
            return result
        finally:
            session.close()


class KeyExtractWrapper(object):

    """本Handler可以将一行中的某个字段转变为Key，并将结果包装为一个字典结构
       例如以第一列为Key：((1, 2, 3, 4, 5), ) => {1: (1, 2, 3, 4, 5)}
       以某个属性为Key: (User(id=0, name="SamChi", age=31),) => {"SamChi": User(...)}
    """

    def __init__(self, key_index):
        """
        :param key_index 作为索引，可以是数字，也可以是字符串属性名
                         具体由行类型来决定
        """
        self._key_index = key_index

    def __call__(self, query_result):
        if not query_result:
            return {}
        row_0 = query_result[0]
        if isinstance(row_0,
                      (types.ListType, types.TupleType, types.DictType)):
            return {row[self._key_index]: row for row in query_result}
        return {getattr(row, self._key_index): row for row in query_result}

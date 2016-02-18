# coding: utf-8

"""参数验证相关工具
"""

import re
import ujson
import types
import numbers
from girlfriend.util.lang import args2fields
from girlfriend.exception import InvalidArgumentException


class Rule(object):

    """描述参数验证规则，并执行验证过程
    """

    @args2fields()
    def __init__(self, name,
                 type=None,
                 required=False, min=None, max=None,
                 regex=None, logic=None, default=None):
        """
        :param name      参数名称，通常用于错误提示
        :param required  如果为True，那么参数是必须的
        :param min       如果是字符串，那么该参数为最小长度(等于此长度合法)，
                         如果是数字(numbers.Number类型)，那么为该参数最小值(等于此值算合法)
        :param max       同上
        :param regex     正则验证
        :param type      类型验证，多个参数可以传递元组
        :param logic     谓词函数，满足更加复杂的业务验证需要，比如查查数据库邮箱是否存在等等
                         该谓词函数并非返回True和False，如果有错误，那么返回错误消息的字符串，
                         如果没有错误，那么直接返回None
        :param default   该项的默认值
        """
        pass

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def required(self):
        return self._required

    def validate(self, value):
        """执行验证
           :param value 要验证的值
        """
        if self._required and self._is_empty(value):
            raise InvalidArgumentException(
                u"参数 '{}' 的值是必须的，不能为空".format(self._name))

        # 如果非必须并且为空，那么接下来的验证就不必运行了
        if self._is_empty(value):
            return

        # 检查类型
        self._validate_type(value)

        # 检查大小、长度
        self._validate_min_max(value)

        # 检查正则
        self._validate_regex(value)

        # 检查逻辑
        self._validate_logic(value)

    def _validate_type(self, value):
        if not self._type:
            return
        if not isinstance(value, self._type):
            raise InvalidArgumentException(
                u"参数 '{name}' 的类型不正确，只允许以下类型：{types}".format(
                    name=self._name,
                    types=self._type
                )
            )

    def _validate_min_max(self, value):
        if self._min is not None:
            if isinstance(value, numbers.Number):
                if self._min > value:
                    raise InvalidArgumentException(
                        u"参数 '{name}' 的值不能小于{min}".format(
                            name=self._name, min=self._min)
                    )
            else:
                if self._min > len(value):
                    raise InvalidArgumentException(
                        u"参数 '{name}' 的长度不能小于{min}".format(
                            name=self._name, min=self._min)
                    )
        if self._max is not None:
            if isinstance(value, numbers.Number):
                if self._max < value:
                    raise InvalidArgumentException(
                        u"参数 '{name}' 的值不能大于{max}".format(
                            name=self._name, max=self._max)
                    )
            else:
                if self._max < len(value):
                    raise InvalidArgumentException(
                        u"参数 '{name}' 的长度不能大于{max}".format(
                            name=self._name, max=self._max)
                    )

    def _validate_regex(self, value):
        if not self._regex:
            return
        value = str(value)
        if not re.search(self._regex, value):
            raise InvalidArgumentException(
                u"参数 '{name}' 不符合正则表达式'{regex}'".format(
                    name=self._name, regex=self._regex)
            )

    def _validate_logic(self, value):
        if self._logic is None:
            return
        msg = self._logic(value)
        if msg:
            raise InvalidArgumentException(msg)

    def _is_empty(self, value):
        """判断一个值是否为空
           如果值为None，那么返回True
           如果值为空字符串，那么返回True
           如果值为0, 那么不算空，返回False
        """
        if value is None:
            return True
        if isinstance(value, types.StringType) and not value:
            return True
        return False


def be_json(name):
    def _be_json(value):
        try:
            ujson.loads(value)
        except:
            return u"参数 '{}' 必须是json格式".format(name)
    return _be_json

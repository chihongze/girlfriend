# coding: utf-8

"""时间操作工具
"""

import re
from girlfriend.exception import InvalidArgumentException

time_unit_regex = re.compile(r"^(\d+)(d|h|m|s)$", re.IGNORECASE)

time_units = {
    "d": 24 * 60 * 60,
    "h": 60 * 60,
    "m": 60,
    "s": 1
}


def parse_time_unit(time_unit):
    """将以下单位描述转换为秒
       1d -> 24 * 60 * 60
       1h -> 1 * 60 * 60
       1m -> 1 * 60
       1s -> 1
    """
    match_result = time_unit_regex.search(time_unit)
    if not match_result:
        raise InvalidArgumentException(u"参数 '{}' 不符合时间单位格式".format(time_unit))
    time_value, unit = (int(match_result.group(1)),
                        match_result.group(2).lower())
    return time_value * time_units[unit]

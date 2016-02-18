# coding: utf-8

"""日志工具模块
   集成了常用的log handler、log formatter和日志创建工具
"""

import sys
import logging
import logging.handlers


LOGGER_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def get_logger_level_by_name(name):
    return LOGGER_LEVELS[name.lower()]


def time_rotating_handler(filename, when="D", interval=1, backupCount=0,
                          encoding="utf-8", delay=False):
    """基于时间回滚的日志策略"""
    return logging.handlers.TimedRotatingFileHandler(
        filename,
        when="D",
        interval=1,
        backupCount=0,
        encoding="utf-8",
        delay=delay
    )


def daily_rotaiting_handler(filename):
    """基于天的日志回滚策略"""
    return time_rotating_handler(filename)


def stdout_handler():
    """标准输出"""
    return logging.StreamHandler(sys.stdout)


LOG_FORMATTER = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def create_logger(logger_name, handlers, level=logging.INFO,
                  formatter=LOG_FORMATTER):
    """创建日志对象
    :param logger_name 日志名称
    :param filename 日志文件路径
    :param level 日志级别
    :param formatter 日志输出格式
    :param handlers 日志处理策略
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    for handler in handlers:
        handler.setFormatter(logging.Formatter(LOG_FORMATTER))
        logger.addHandler(handler)
    return logger

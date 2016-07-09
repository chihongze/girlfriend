# coding: utf-8

"""基于Pickle的持久化方案
"""

from __future__ import absolute_import

import pickle
from girlfriend.workflow.persist.file import (
    AbstractFilePersistListener,
    AbstractFileRecoverPolicy
)


class PicklePersistListener(AbstractFilePersistListener):

    """基于Pickle的工作流持久化监听器
    """

    def __init__(self, dump_to="dump.dat"):
        super(PicklePersistListener, self).__init__(dump_to)

    def _dump_data_to_file(self, data, file):
        pickle.dump(data, file)


class PickleRecoverPolicy(AbstractFileRecoverPolicy):

    """基于Pickle的工作流中断恢复策略
    """

    def __init__(self, dump_to="dump.dat"):
        super(PickleRecoverPolicy, self).__init__(dump_to)

    def _load_data(self, file):
        return pickle.load(file)

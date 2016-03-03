# coding: utf-8


class ReadTextPlugin(object):

    def execute(self, context, *readers):
        return [reader(context) for reader in readers]


class FileReader(object):
    pass

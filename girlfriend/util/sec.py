# coding: utf-8

import md5


def md5encode(content):
    return md5.new(content).hexdigest()

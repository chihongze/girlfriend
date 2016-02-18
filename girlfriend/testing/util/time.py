# coding: utf-8

from girlfriend.util.time import parse_time_unit
from girlfriend.testing import GirlFriendTestCase


class TimeUtilTestCase(GirlFriendTestCase):

    def test_parse_time_unit(self):
        self.assertEquals(parse_time_unit("2d"), 2 * 24 * 60 * 60)
        self.assertEquals(parse_time_unit("3h"), 3 * 60 * 60)
        self.assertEquals(parse_time_unit("5m"), 5 * 60)
        self.assertEquals(parse_time_unit("30000s"), 30000)

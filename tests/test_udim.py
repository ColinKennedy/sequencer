#!/usr/bin/env python
# -*- coding: utf-8 -*-

# IMPORT STANDARD LIBRARIES
import itertools
import unittest
import random
import sys

# IMPORT LOCAL LIBRARIES
import sequencer.udim_iterator


class ExpectingTestCase(unittest.TestCase):
    def run(self, result=None):
        self._result = result
        self._num_expectations = 0
        super(ExpectingTestCase, self).run(result)

    def _fail(self, failure):
        try:
            raise failure
        except failure.__class__:
            self._result.addFailure(self, sys.exc_info())

    def expect_true(self, a, msg):
        if not a:
            self._fail(self.failureException(msg))
        self._num_expectations += 1

    def expect_equal(self, a, b, msg=''):
        if a != b:
            msg = '({}) Expected {} to equal {}. ' \
                  ''.format(self._num_expectations, a, b) + msg
            self._fail(self.failureException(msg))
        self._num_expectations += 1


class UdimBase(ExpectingTestCase):

    '''A test for the base UDIM class.'''

    def setUp(self):
        '''Create example UDIM indexes and their Mari UDIM values.'''
        self.udims_raw = \
            (0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
             100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
             200, 201, 202, 203, 204, 205, 206, 207, 208, 209,
             300, 301, 302, 303, 304, 305, 306, 307, 308, 309)

        self.udims = \
            (1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010,
             1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110,
             1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210,
             1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310,
             1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408, 1409, 1410,
             1501, 1502, 1503, 1504, 1505, 1506, 1507, 1508, 1509, 1510,
             1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610,
             1701, 1702, 1703, 1704, 1705, 1706, 1707, 1708, 1709, 1710,
             1801, 1802, 1803, 1804, 1805, 1806, 1807, 1808, 1809, 1810,
             1901, 1902, 1903, 1904, 1905, 1906, 1907, 1908, 1909, 1910,
             2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
             2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110)


class UdimBaseTestCase(UdimBase):

    '''Test the UDIM base class.'''

    def test_udim_base_jump(self):
        '''Make sure that UDIMs jump to the correct values and positions.'''
        expected_udims = self.udims_raw[:10]
        iterator = udim_iterator.UdimBaseIterator(101)
        for expected_index, index in itertools.izip(expected_udims, iterator):
            self.expect_equal(index, expected_index)


class UdimTestCase(UdimBase):

    '''Test the UDIM helper subclass.'''

    def get_and_test_udim_range(self, start=0, end=0):
        '''Create a UDIM range and tests it against the generated UDIMs.

        If one arg is given to the method, it is assumed that start=0 and
        end=the_number.

        Args:
            start (:obj:`bool`, optional): The first UDIM in the range to test.
            end (:obj:`bool`, optional): The last UDIM in the range to test.

        '''
        if not start and not end:
            raise ValueError(
                'You need to specify a value to get_and_test_udim_range.')

        if start > end:
            start, end = end, start

        udims = self.udims[start:end]
        iterator = udim_iterator.UdimIterator(start=start, end=end)
        error_message = 'Start/End: "{0}/{1}"'.format(start, end)
        for expected_index, index in itertools.izip(udims, iterator):
            offset_index = index + 1001
            self.expect_equal(expected_index, offset_index, error_message)

    def test_udim_no_skip_range(self):
        '''Check a UDIM range that does not skip.'''
        number_of_udims = 9
        self.get_and_test_udim_range(number_of_udims)

    def test_udim_range_0001(self):
        '''Check a random UDIM range that previously failed our tests.'''
        start = 5
        end = 23
        self.get_and_test_udim_range(start=start, end=end)

    def test_udim_range_0002(self):
        '''Check that the UDIM range jumps correctly.'''
        start = 9
        end = 11
        self.get_and_test_udim_range(start=start, end=end)

    def test_udim_range_0003(self):
        '''Make sure that single UDIM tests are possible.'''
        start = 1
        end = 2
        self.get_and_test_udim_range(start=start, end=end)

    def test_udim_range_0004(self):
        '''Check another range that failed.'''
        start = 1
        end = 34
        self.get_and_test_udim_range(start=start, end=end)

    def test_random_udim_range(self):
        '''Generate random tests (to try to find failing edge-cases).'''
        start = random.randint(0, 99)
        end = random.randint(0, 99)
        self.get_and_test_udim_range(start=start, end=end)


class Udim2DTestCase(UdimBase):

    '''A collection of tests for a Mudbox/Zbrush-style, 2D UDIM.'''

    def setUp(self):
        '''Create example UDIM indexes, for a 2D-style UDIM.'''
        self.udims = ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4),
                      (0, 5), (0, 6), (0, 7), (0, 8), (0, 9),

                      (1, 0), (1, 1), (1, 2), (1, 3), (1, 4),
                      (1, 5), (1, 6), (1, 7), (1, 8), (1, 9),

                      (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
                      (2, 5), (2, 6), (2, 7), (2, 8), (2, 9),

                      (3, 0), (3, 1), (3, 2), (3, 3), (3, 4),
                      (3, 5), (3, 6), (3, 7), (3, 8), (3, 9),

                      (4, 0), (4, 1), (4, 2), (4, 3), (4, 4),
                      (4, 5), (4, 6), (4, 7), (4, 8), (4, 9),

                      (5, 0), (5, 1), (5, 2), (5, 3), (5, 4),
                      (5, 5), (5, 6), (5, 7), (5, 8), (5, 9),

                      (6, 0), (6, 1), (6, 2), (6, 3), (6, 4),
                      (6, 5), (6, 6), (6, 7), (6, 8), (6, 9),

                      (7, 0), (7, 1), (7, 2), (7, 3), (7, 4),
                      (7, 5), (7, 6), (7, 7), (7, 8), (7, 9),

                      (8, 0), (8, 1), (8, 2), (8, 3), (8, 4),
                      (8, 5), (8, 6), (8, 7), (8, 8), (8, 9),

                      (9, 0), (9, 1), (9, 2), (9, 3), (9, 4),
                      (9, 5), (9, 6), (9, 7), (9, 8), (9, 9))

    def get_and_test_udim_range(self, start=0, end=0):
        '''Create a UDIM range and tests it against the generated UDIMs.

        If one arg is given to the method, it is assumed that start=0 and
        end=the_number.

        Args:
            start (:obj:`bool`, optional): The first UDIM in the range to test.
            end (:obj:`bool`, optional): The last UDIM in the range to test.

        '''
        if not start and not end:
            raise ValueError(
                'You need to specify a value to get_and_test_udim_range.')

        if start > end:
            start, end = end, start

        udims = self.udims[start:end]
        iterator = udim_iterator.UdimIterator2D(start=start, end=end)
        error_message = 'Start/End: "{0}/{1}"'.format(start, end)
        for (expected_x, expected_y), (x_index, y_index) \
                in itertools.izip(udims, iterator):
            self.expect_equal(
                (expected_x, expected_y), (x_index, y_index), error_message)

    def test_no_jump(self):
        '''Get a UDIM range that doesn't increment the x (0th) index.'''
        start = 0
        end = 5

        self.get_and_test_udim_range(start=start, end=end)

    def test_udim_jump(self):
        '''Check that UDIM jumps work properly.'''
        start = 1
        end = 11

        self.get_and_test_udim_range(start=start, end=end)

    def test_random_udim_range(self):
        '''Generate random tests (to try to find failing edge-cases).'''
        start = random.randint(0, 99)
        end = random.randint(0, 99)
        self.get_and_test_udim_range(start=start, end=end)

    def test_udim_range_0001(self):
        iterator = udim_iterator.UdimIterator2D(start=[0, 0], end=[1, 1])

        # [0, 0] -> [1, 0]
        expected_udims = self.udims[:11]
        generated_udims = tuple(item for item in iterator)

        self.assertEqual(expected_udims, generated_udims)


if __name__ == '__main__':
    print(__doc__)


#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Iterator classes for UDIMs - 1D and 2D UDIMs.'''

# IMPORT STANDARD LIBRARIES
from __future__ import division

# IMPORT THIRD-PARTY LIBRARIES
from six.moves import range
import six

# IMPORT LOCAL LIBRARIES
from .core import check


class UdimBaseIterator(six.Iterator):

    '''Force numbers in the UDIM to skip, based on some arbitrary width.

    Note:
        This class operates on base 0. It is not meant to be used, directly.
        If you need a Mari-style UDIM iterator, use UdimIterator or some other
        subclass, if it exists after the time of writing
        (2017-06-10 15:27:39.511833).

    '''

    def __init__(self, start=0, end=0, width=10):
        '''Create the iterator and set its target value.

        Args:
            start (int): The minimum value that this object will build towards.
            end (int): The maximum value that this object will build towards.
            width (:obj:`int`, optional):
                The point in which a UDIM value should skip. Default: 10.

        Raises:
            ValueError: A UDIM cannot have a negative shell value.
                        The start variable must be >= 0.

        '''
        super(UdimBaseIterator, self).__init__()
        if start > end:
            start, end = end, start

        if start < 0:
            raise ValueError('Starting value cannot be less than zero.')

        self.start = start
        self.end = end
        self.width = width

    def __iter__(self):
        '''Iterate over this object and yield values until it hits its maximum.

        Yields:
            int: UDIM values.

        '''
        values = [number for number in range(self.start, self.end)]
        for value in values:
            yield (value // self.width) * 100 + value % self.width


class UdimIterator(UdimBaseIterator):

    '''Optimize the base iterator to have more convenient input values.'''

    def __init__(self, start=0, end=0, width=10, udim_type='raw'):
        '''Convert the value to work with the base iterator.

        Args:
            start (int): The beginning of this udim sequence iteraor.
            end (int): The end of this udim sequence iteraor.
            width (:obj:`int`, optional):
                The point in which a UDIM value should skip. Default: 10.
            udim_type (:obj:`str`, optional):
                A strategy to conform the given start/end values to something
                that this class can understand. There are several types.

                'raw': Do nothing to the passed values. Don't convert them.
                'mari': The given UDIM values come from Mari
                        and need to be converted.

                Default: 'raw'.

        '''
        def convert_mari_to_iterator(value):
            '''int: Change a Mari index to a value that this iterator uses.'''
            value = int(value)
            value -= 1000
            return ((value // 100) * 10) + value % 10

        def convert_raw_to_iterator(value):
            '''Return the original value and do nothing.'''
            return value

        def convert_to_iterator_value(value):
            '''int: Convert value to something that this iterator can use.'''
            udim_options = \
                {
                    'raw': convert_raw_to_iterator,
                    'mari': convert_mari_to_iterator,
                }

            try:
                converter = udim_options[udim_type]
            except KeyError:
                raise ValueError(
                    'Got UDIM type: "{udim}" but expected one of "{opt}".'
                    ''.format(udim=udim_type, opt=sorted(udim_options.keys())))

            return converter(value)

        if start > end:
            start, end = end, start

        start = convert_to_iterator_value(start)
        end = convert_to_iterator_value(end)

        super(UdimIterator, self).__init__(start=start, end=end)


class UdimIntAdapter(object):

    '''A class that will make dealing with 1D/2D UDIM indexes less painful.'''

    def __init__(self, value, width=10):
        '''Store the given value.

        Args:
            value (int): The value to adapt.
            width (:obj:`int`, optional):
                The point in which a UDIM value should skip. Default: 10.

        '''
        super(UdimIntAdapter, self).__init__()
        self.value = value
        self.width = width

    def __iadd__(self, value):
        '''Convert the value to something is object can understand and += it.

        Args:
            value (int or tuple[int, int]): The value to increment this object.

        '''
        if not isinstance(value, int):
            value = convert_2d_to_index(value, self.width)
        self.value += value


class UdimIterator2D(UdimIterator):

    '''Create a 2D UDIM representation, for Zbrush and Mudbox.'''

    # The number of X UDIM shells allowed before you must increment

    def __init__(self, start=0, end=0, width=10):
        '''Create the instance and pass its value, directly.

        Args:
            start (int): The minimum value that this object will build towards.
            end (int): The maximum UDIM value to iterate over.
            width (:obj:`int`, optional):
                The point in which a UDIM value should skip. Default: 10.

        '''
        self._end = None  # Give it some default value, just in case
        self._start = None  # Give it some default value, just in case
        self.width = width

        if check.is_itertype(start) and len(start) == 2:
            start = convert_2d_to_index(start, width=self.width)

        if check.is_itertype(end) and len(end) == 2:
            end = convert_2d_to_index(end, width=self.width)

        super(UdimIterator2D, self).__init__(start=start, end=end)

    def _increment_value(self, value):
        '''Get the next appropriate value for some UDIM value.

        Args:
            value (int or tuple[int, int]): The value to increment.

        Returns:
            int: The next value up from this value.

        '''
        return increment_multi_udim_value(value, self.width)

    @property
    def end(self):
        '''int: The 1D index that is the end of this UDIM.'''
        return self._end.value

    @end.setter
    def end(self, value):
        '''Put that value into an adapter and store it on this object.'''
        self._end = UdimIntAdapter(value)

    def __iter__(self):
        '''Convert the base __iter__ into a 2D array.'''
        results = super(UdimIterator2D, self).__iter__()
        for result in results:
            yield (result // 100, result % 100)


def convert_index_to_2d(value, width):
    '''Change a 1D index to a 2D index.

    Args:
        value (int): The value to make 2D.
        width (int): The frequency that value will be incremented, vertically.
                     Think of it like the width of an image, if needed.

    Returns:
        tuple[int, int]: The converted value.

    '''
    return (value // width, value % width)


def convert_2d_to_index(value, width):
    '''Take a UDIM index (two integers) and convert it to a 1D index (int).

    Args:
        value (tuple[int, int]): The index shell position (width and height).
        width (int):
            How number when the shells must shift. For example, with UDIMs,
            the width is always 10, but any value could be used.

    Returns:
        int: The index that represents this 2D sequence.

    '''
    if check.is_itertype(value) and len(value) == 2:
        value_x, value_y = value
        return (value_x * width) + value_y

    # If the given value was just an index, do nothing and return it
    return value


def increment_multi_udim_value(value, width):
    '''Get the next appropriate value for some UDIM value.

    Args:
        value (int or tuple[int, int]): The value to increment.
        width (int):
            How number when the shells must shift. For example, with UDIMs,
            the width is always 10, but any value could be used.

    Returns:
        int: The next value up from this value.

    '''
    if isinstance(value, int):
        value_x, value_y = convert_index_to_2d(value, width)
        if value_y + 1 > width:
            value_x += 1
        else:
            value_y += 1

    return convert_2d_to_index([value_x, value_y], width)


if __name__ == '__main__':
    print(__doc__)


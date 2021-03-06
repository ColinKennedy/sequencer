#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''A class and module to describe a single item with a sequence of items.'''

# IMPORT STANDARD LIBRARIES
import itertools
import os
import re

# IMPORT THIRD-PARTY LIBRARIES
from cached_property import cached_property
from six.moves import range

# IMPORT LOCAL LIBRARIES
from .core import check


class SequenceItem(object):

    '''An item of a sequence. It contains a path, value, and other information.

    Note:
        This class assumes that the increments used are integers.

    '''

    def __init__(self, path):
        '''Create the object and store its path.

        Args:
            path (str):
                The path to the object. The path can be absolute or relative
                but it must have a value to indicate that's part of a sequence.
                Example: one or more digits.

        '''
        super(SequenceItem, self).__init__()
        self._path_delimiter = None
        self.path = path

    @cached_property
    def path_delimiter(self):
        '''Determine the best way to split the path into sections and store it.

        When self.path_delimiter is run, its choices are iterated through until
        the best choice for the path is found. That choice is compiled and
        cached and then returned.

        In each iteration, if a choice doesn't work, the cache is invalidated
        and the next choice is tried until a choice is found.

        Raises:
            NotImplementedError: If path delimiter couldn't be determined for
                                 the stored path.

        Returns:
            <re._compile>: The compiled regex object.

        '''
        if self._path_delimiter is not None:
            return self._path_delimiter

        for choice in self._path_delimiter_choices():
            path_delimiter = re.compile(choice)

            try:
                del self.__dict__['path_delimiter']
            except KeyError:
                pass

            self._path_delimiter = path_delimiter

            try:
                self.get_value()
            except ValueError:
                pass
            else:
                return path_delimiter

        raise NotImplementedError(
            'Path: "{path}" could not be split using, "{opt}". Not sure how to '
            'handle this situation.'.format(
                path=self.path, opt=self._path_delimiter_choices))

    @classmethod
    def _path_delimiter_choices(cls):
        '''tuple[str]: The regex choices to use as a path delimiter.

        Warning:
            The method makes it difficult to define custom logic to what
            choices to use.

        '''
        return (r'(\.)(\d+)', r'(_[uv])(\d+)')

    def _split_delimiter(self, path):
        '''Find the correct method to split the path into digits and split it.

        Note:
            To get the original path again, you can take the result of this
            method and just ''.join() it back together.

        Args:
            path (str): The path to split into pieces.

        Returns:
            tuple[str]: The path, split into pieces.

        '''
        def split_by_group(path, re_compile):
            '''Todo: Possibly make this the canonical split method logic.'''
            temp_list = [str_ for str_ in re_compile.split(path) if str_]
            temp_list[0:2] = [''.join(temp_list[0:2])]
            return temp_list

        return tuple(split_by_group(path, self.path_delimiter))

    def has_matching_path_template(self, path):
        '''bool: If this object and the path have the same root path.'''
        current_root_path = os.path.dirname(self.path)
        other_root_path = os.path.dirname(path)

        path_object = self.__class__(path)
        other_formatted_path = path_object.get_formatted_path()

        return current_root_path == other_root_path \
            and self.get_formatted_path() == other_formatted_path

    def get_parts(self, as_type=int):
        '''Get the digit and non-digit parts of this item.

        Args:
            as_type (callable): A function to run on the found digits in parts.
                                Default: int wrapper function.

        Returns:
            tuple[tuple[str], tuple[int]]: The non-digit parts and digit parts.

        '''
        digits = []
        non_digits = []
        for part in self._split_delimiter(self.path):
            if part.isdigit():
                digits.append(as_type(part))
            else:
                non_digits.append(part)

        return (tuple(non_digits), tuple(digits))

    def get_digits(self, as_type=int):
        '''Get only the digits in this object instance.

        Args:
            as_type (callable): A function to run on the found digits in parts.
                                Default: int wrapper function.

        Returns:
            tuple[as_type]: The digits of this path.

        '''
        return self.get_parts(as_type=as_type)[1]

    def get_non_digits(self):
        '''tuple[str]: Get the parts of this instance that are not digits.'''
        return self.get_parts()[0]

    def get_formatted_path(self):
        '''Get the current path, in a Python-format-style string.

        Note:
            This format does not assume padding. Instead of {:04d},
            a like file.1001.tif will just return file.{}.tif.

        Returns:
            str: The formatted path.

        '''
        return '{}'.join(self.get_non_digits())

    def get_dimensions(self):
        '''int: The number of varying digits in the path.'''
        return len([item for item in self._split_delimiter(self.path)
                    if item.isdigit()])

    def get_value(self):
        '''Get the stored digit(s) on this object.

        Raises:
            If no digits were found.

        Returns:
            int or list[int]: The sequence value that this object represents.

        '''
        digits = self._split_delimiter(os.path.basename(self.path))
        digits = [int(value) for value in digits if value.isdigit()]

        if not digits:
            raise ValueError('Something went wrong. Does path have a digit? '
                             '"{path}".'.format(path=self.path))

        if len(digits) == 1:
            return digits[0]
        return list(digits)

    def _conform_value_iterable(self, value, position):
        '''Force the value to work with positions.

        Since items can be 1D or multi-dimensioned, value and position may
        or may not need to be iterable (It the item is 1D, it doesn't but if
        it's 2D, it needs to be iterable).

        Basically, this is a convenience method.

        Args:
            value (int or tuple[int]): The value(s) to change on this path.
            position (int or tuple[int]): The index(es) which each value change.

        Raises:
            ValueError:
                If this object is multi-dimensional (2+ dimensions, like a UDIM)
                and no position was given or the value given doesn't match the
                dimensions, we can't reasonably guess what to set the value to.

        Returns:
            tuple[list[int], list[int]]: The iterable values and positions.

        '''
        value, position = make_value_position_iterable(
            value, position, dimensions=self.get_dimensions())
        return (value, position)

    def get_padding(self, position=None):
        '''Get the padding of some point of this item.

        If this item is multi-dimensional and position is not given, every
        padding position is returned.

        Args:
            position (int or tuple[int]): The index(es) which each value change.

        Returns:
            int or tuple[int]: The padding at each digit on this item.
                               If the seqeuence is one dimensional, the value
                               that returns is not iterable.

        '''
        parts = self._split_delimiter(self.path)
        digit_parts = [len(part) for part in parts if part.isdigit()]

        if self.get_dimensions() == 1:
            if position is None:
                position = 0

            return digit_parts[position]  # Note: early return

        digit_parts, position = self._conform_value_iterable(
            digit_parts, position)

        paddings = []
        for position_ in position:
            paddings.append(digit_parts[position_])

        return tuple(paddings)

    def set_padding(self, value, position):
        '''Change the padding(s) on this item, using values and positions.

        Args:
            value (int or tuple[int]): The value(s) to set padding on this path.
            position (int or tuple[int]): The index(es) which each value change.

        '''
        paddings = self.get_padding()
        paddings = check.force_itertype(paddings)  # Returns a list - important

        value, position = self._conform_value_iterable(
            value, position)

        for value_, position_ in itertools.izip(value, position):
            paddings[position_] = value_

        parts = self._split_delimiter(self.path)
        digit_parts = [int(part) for part in parts if part.isdigit()]

        padding_digits = []
        for padding, digit in itertools.izip(paddings, digit_parts):
            padding_digits.append(str(digit).zfill(padding))

        self.path = self.get_formatted_path().format(*padding_digits)

    def set_value(self, value, position=None):
        '''Change the value of this item and its path representation.

        If a value is 10 and the position is 0, the 0th digit on this item
        will be set with the number 1. If value is 13 and position is 1 and this
        item is 2-dimensional, the 1st digit position will be set to 13.

        Args:
            value (int or tuple[int]): The value(s) to change on this path.
            position (int or tuple[int]): The index(es) which each value change.

        '''
        value, position = self._conform_value_iterable(
            value, position)

        parts = self._split_delimiter(self.path)
        non_digit_parts = [None if part.isdigit() else part for part in parts]
        digit_parts = [part for part in parts if part.isdigit()]

        for position_, value_ in itertools.izip(position, value):
            # Note: This assumes that there is padding on image
            padding = '{:0' + str(len(digit_parts[position_])) + 'd}'
            digit_parts[position_] = padding.format(value_)

        final_path = ''
        current_digit_index = 0
        for part in non_digit_parts:
            if part is None:
                part = digit_parts[current_digit_index]
                current_digit_index += 1
            final_path += part

        self.path = final_path

    def promote_to_sequence(self, path):
        '''Create a sequence, using this path and the given path.

        The start/end range of the sequence is automatically determined by
        finding out if the path is a lower value than the current object.

        Args:
            path (str): The path to make a start or end point of a sequence.

        Raises:
            ValueError: If the paths don't have matching names.
            ValueError: If the path's value matches the current object's value.

        Returns:
            Sequence: The sequence that was automatically created.

        '''
        from . import sequencer

        def replace_digit_with_hash(match):
            '''str: Some varying number of '#' for match. Match must be > 0.'''
            return '#' * len(match.group(1))

        if not self.has_matching_path_template(path):
            raise ValueError('Path: "{path}" cannot be added to "{seq!r}" '
                             'because the two paths are not matching.'
                             ''.format(path=path, seq=self))
        end_item = self.__class__(path)
        start_item = self

        if start_item.get_value() == end_item.get_value():
            raise ValueError('Path must be different from the current path.')

        if start_item.get_value() > end_item.get_value():
            start_item, end_item = end_item, start_item

        # Note: This assumes that the path(s) are padding sensitive. This may
        #       cause issues in the future.
        #
        formatted_path = re.sub(r'(\d+)', replace_digit_with_hash, self.path)
        return sequencer.Sequence(formatted_path, start=start_item.get_value(),
                                  end=end_item.get_value())

    def __str__(self):
        '''str: The path of this object instance.'''
        return self.path

    def __repr__(self):
        '''str: The code needed to re-create this object.'''
        return "{name}('{path}')".format(name=self.__class__.__name__,
                                         path=self.path)


def make_value_position_iterable(value, position, dimensions):
    '''Force the value to work with positions.

    Args:
        value (int or tuple[int]): The value(s) to change on this path.
        position (int or tuple[int]): The index(es) which each value change.
        dimensions (int): The max length that value and position can be.

    Raises:
        ValueError:
            If this object is multi-dimensional (2+ dimensions, like a UDIM)
            and no position was given or the value given doesn't match the
            dimensions, we can't reasonably guess what to set the value to.

    Returns:
        tuple[list[int], list[int]]: The iterable values and positions.

    '''
    value = check.force_itertype(value)

    if position is None:
        position_ = [position_ for position_ in range(len(value))]
    else:
        position_ = check.force_itertype(position)

    if position is None and len(value) != dimensions:
        raise ValueError('Value: "{val}" is invalid. You must specify an '
                         'index or give "{dim}" values, at once.'
                         ''.format(val=value, dim=dimensions))

    return (value, position_)


if __name__ == '__main__':
    print(__doc__)


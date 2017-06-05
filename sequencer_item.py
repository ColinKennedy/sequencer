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
# TODO : Make relative
from core import check


# TODO : Make __repr__ for SequenceItem, Sequence, and nested Sequence
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

        raise NotImplementedError('Not sure how to handle this situation')

    @classmethod
    def _path_delimiter_choices(cls):
        '''tuple[str]: The regex choices to use as a path delimiter.

        Warning:
            The method makes it difficult to define custom logic to what
            choices to use.

        '''
        return (r'(\.)(\d+)', r'(_[uv])(\d+)')

    def __split_delimiter(self, path):
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

        # # I can't figure out how to get what I want so I made this ghetto thing
        # # This should definitely be optimized
        # # example: self.path = '/some/path_u1_v2.tif' ->
        # #                      ['/some/path_u', '1', '_v', '2', '.tif']
        # #
        # # TODO : Make this method less magical
        # #
        # split_items = []
        # for match in self.path_delimiter.finditer(path):
        #     split_items.extend(match.groups())

        # final_split = []
        # split_items_len = len(split_items)
        # last_end = None
        # for index, item in enumerate(split_items):
        #     starting_index = path.index(item)

        #     if index == 0:
        #         final_split.append(path[:starting_index])

        #     if last_end is not None and starting_index != last_end:
        #         final_split.append(path[last_end:starting_index])

        #     ending_index = starting_index + len(item)
        #     last_end = ending_index
        #     final_split.append(path[starting_index:ending_index])

        #     if index + 1 == split_items_len:
        #         final_split.append(path[ending_index:])

        # return tuple(final_split)

    def has_matching_path_template(self, path):
        '''bool: If this object and the path have the same root path.'''
        current_root_path = os.path.dirname(self.path)
        other_root_path = os.path.dirname(path)

        path_object = self.__class__(path)
        other_formatted_path = path_object.get_formatted_path()

        return current_root_path == other_root_path \
            and self.get_formatted_path() == other_formatted_path

    def get_digits(self, as_type=int):
        '''tuple[as_type]: The digits of this path.'''
        return tuple(as_type(item) for item in self.__split_delimiter(self.path)
                     if item.isdigit())

    def get_formatted_path(self):
        '''Get the current path, in a Python-format-style string.

        Note:
            This format does not assume padding. Instead of {:04d},
            a like file.1001.tif will just return file.{}.tif.

        Returns:
            str: The formatted path.

        '''
        return '{}'.join(
            [item for item in self.__split_delimiter(self.path)
             if not item.isdigit()])

    def get_dimensions(self):
        '''int: The number of varying digits in the path.'''
        return len([item for item in self.__split_delimiter(self.path)
                    if item.isdigit()])

    def get_value(self):
        '''int or list[int]: The sequence value that this object represents.'''
        digits = self.__split_delimiter(os.path.basename(self.path))
        digits = [int(value) for value in digits if value.isdigit()]

        if not digits:
            raise ValueError('Something went wrong. Does path have a digit? '
                             '"{path}".'.format(path=self.path))

        if len(digits) == 1:
            return digits[0]
        return list(digits)

    def set_value(self, value, position=None):
        '''Change the value of this item and its path representation.

        Args:
            value (int or tuple[int]): The value(s) to change on this path.
            position (int or tuple[int]): The index(es) which each value changes.

        Raises:
            ValueError:
                If this object is multi-dimensional (2+ dimensions, like a UDIM)
                and no position was given or the value given doesn't match the
                dimensions, we can't reasonably guess what to set the value to.

        '''
        value = check.force_itertype(value)

        if position is None:
            position_ = [position_ for position_ in range(len(value))]
        else:
            position_ = check.force_itertype(position)

        if position is None and len(value) != self.get_dimensions():
            raise ValueError('Value: "{val}" is invalid. You must specify an '
                             'index or give "{dim}" values, at once.'
                             ''.format(val=value, dim=self.get_dimensions()))

        parts = self.__split_delimiter(self.path)
        non_digit_parts = [None if part.isdigit() else part for part in parts]
        digit_parts = [part for part in parts if part.isdigit()]

        for position_, value_ in itertools.izip(position_, value):
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
        # TODO : Make relative
        import sequencer

        def replace_digit_with_pound(match):
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
        formatted_path = re.sub(r'(\d+)', replace_digit_with_pound, self.path)
        return sequencer.Sequence(formatted_path, start=start_item.get_value(),
                                  end=end_item.get_value())

    def __str__(self):
        '''str: The path of this object instance.'''
        return self.path

    def __repr__(self):
        '''str: The code needed to re-create this object.'''
        return "{name}('{path}')".format(name=self.__class__.__name__,
                                         path=self.path)


if __name__ == '__main__':
    print(__doc__)


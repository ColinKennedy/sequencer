#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''A collection of classes and functions to describe sequences.

Sequences are defined as any continuous elements. The minimum requirement
for a sequence is 3 consecutive items.

'''

# IMPORT STANDARD LIBRARIES
import collections
import functools
import itertools
import operator
import textwrap
import copy
import re

# IMPORT THIRD-PARTY LIBRARIES
from six.moves import range
import six

# IMPORT LOCAL LIBRARIES
from . import sequencer_item
from . import udim_iterator
from .core import grouping
from .core import textcase
from . import conversion
from .core import check


class Range(object):

    # Note:
    #     This class is less important than <udim_iterator.UdimIterator2D>,
    #     which actually has rules on how its values are allowed to increment.
    #

    '''A thin wrapper around the built-in "range" function.

    If you need the ability to make a range and change its values after
    instantiation, this is a simple way to do it.

    '''

    def __init__(self, start=0, end=0, step=1):
        '''Create the range object like the regular range object.

        Args:
            start (:obj:`int`, optional): The index of the range to iterate.
            end (:obj:`int`, optional): The index of a range to stop iterating.
            step (:obj:`int`, optional): The rate that the range travels
                                         from start to end.

        '''
        super(Range, self).__init__()
        if start > end:
            start, end = end, start

        self.start = start
        self.end = end
        self.step = step

    def __iter__(self):
        '''Build the values for this range object.'''
        for value in range(self.start, self.end, self.step):
            yield value


class Sequence(collections.MutableSequence):

    '''A basic object to describe a sequence of items.

    Note:
        This sequence does not have to be continuous. Other sequences can be
        added to this sequence, too. The only requirement of a Sequence object
        is that none of its items or inner sequences overlap.

    '''

    INDENT = 0

    def __init__(self, template, start=0, end=0):
        '''Create the object with its initial sequence values.

        Warning:
            To make this object easier to init, if only a template and a
            single number is given, it is assumed that the number is meant
            to represent the end, NOT the start. This mimics the way that
            Python's "range()" function works.

        Note:
            If a list of files are given, it is assumed that those files are
            meant for only 1 sequence and are all related. If they aren't,
            the sequence won't be created correctly.

        Example:
            >>> sequence = Sequence('/something.####.tif', 0, 10)
            >>> sequence.start  # 0
            >>> sequence.end  # 10

            >>> sequence = Sequence('/something.####.tif', 3, 10)
            >>> sequence.start  # 3
            >>> sequence.end  # 10

            >>> sequence = Sequence('/something.####.tif', 10)
            >>> sequence.start  # 0
            >>> sequence.end  # 10

        Args:
            template (str or list[str]):
                The sequence that this object represents.

                Multiple syntaxes are supported for this object.
                For a padding-insensitive sequence, use a glob form
                (example: '/some/sequence.*.tif').
            start (:obj:`int`, optional):
                The beginning of this sequence. Default: 0.
            end (:obj:`int`, optional):
                The end of the sequence. Default: 0.

        '''
        def get_format_info_hash(padding, length):
            '''list[str]: The items to fill in for some format.'''
            return ['#' * padding] * length

        def get_format_info_glob(padding, length):
            '''list[str]: The items to fill in for some format.'''
            return ['*'] * length

        super(Sequence, self).__init__()

        is_empty_sequence = start == 0 and end == 0 and \
            isinstance(template, six.string_types)

        if not isinstance(template, six.string_types):
            # assuming these are sequence items, we need to create a valid
            # sequence template for these items, get its range, and create
            # a sequence using that info
            #
            items = [self.get_sequence_item(item) for item in template]
            has_consistent_padding = all([item.get_padding() for item in items])

            example_item = items[0]

            # Choose a padding insensitive type or sensitive type
            # (glob vs hash, for example)
            #
            if has_consistent_padding:
                format_info_func = get_format_info_hash
            else:
                format_info_func = get_format_info_glob

            # Create a valid template and set it + the sequence start and end
            format_info = format_info_func(padding=example_item.get_padding(),
                                           length=example_item.get_dimensions())

            template = items[0].get_formatted_path().format(*format_info)
            start = min(item.get_value() for item in items)
            end = max(item.get_value() for item in items)

        if start > end:
            start, end = end, start

        self.template = template
        self.repr_sequence = conversion.get_repr_container(self.template)
        if self.repr_sequence is None:
            # Assume that the user gave an actual path to an item
            # (like /some/path.1001.tif, instead of /some/path.####.tif)
            #
            # If that's the case, default to a glob-type and assume there is
            # no padding
            #
            self.repr_sequence = conversion.REPR_SEQUENCES['glob']
            non_digits = self._tokenize_sequence_path()[0]
            formatted_template = '*'.join(non_digits)

            value = self.get_sequence_item(self.template).get_value()
            start = (value, )
            end = (value, )
        else:
            formatted_template = self.repr_sequence['to_format'](self.template)

            if is_empty_sequence:
                # Create some bogus values for start and end so that we can get away
                # with not actually having any know start/end bounds
                #
                dimensions = conversion.get_dimensions(formatted_template)
                start = tuple(0 for item in range(dimensions))
                end = tuple(0 for item in range(dimensions))

        # As a precaution, in case this template is a 2D sequence
        # (like a UDIM) wrap all start/end values into lists
        #
        start = check.force_itertype(start)
        end = check.force_itertype(end)

        self.start_item = self.get_sequence_item(formatted_template.format(*start))
        self.end_item = self.get_sequence_item(formatted_template.format(*end))

        self.items = self.get_range_items()

    def get_range_items(self):
        '''list[SequenceItem]: Using this object's start/end, create a range.'''
        start = self.get_start()
        end = self.get_end()

        if not start and not end or \
                (check.is_itertype(start) and check.is_itertype(end) and
                 all(dimension == 0 for dimension in start) and
                 all(dimension == 0 for dimension in end)):
            return []

        range_iterator = self._items_iterator(start, end)
        # We need to += 1 because a traditional range doesn't return the last
        # element of a sequence but, in our case, we want it as the default
        # behavior
        #
        range_iterator.end += 1

        items = []
        for index in range_iterator:
            index = check.force_itertype(index)
            item = self.get_sequence_item(
                self.get_format_path().format(*index))
            items.append(item)

        return items

    @classmethod
    def get_sequence_item_class(cls):
        '''SequenceItem: The class that describes an item in the sequence.'''
        return sequencer_item.SequenceItem

    @classmethod
    def get_sequence_item(cls, *args, **kwargs):
        '''Create an item object for this sequence.

        Args:
            *args (list): Positional args that will be passed to the item.
            *kwargs (list): Positional args that will be passed to the item.

        Returns:
            SequenceItem: A single point of reference in this sequence.

        '''
        return cls.get_sequence_item_class()(*args, **kwargs)

    @classmethod
    def _items_iterator(cls, *args, **kwargs):
        '''Range: An adaptive range object that builds, on iteration.'''
        return Range(*args, **kwargs)

    @property
    def dimensions(self):
        '''int: The number of positions where this object has digits.'''
        raise NotImplementedError('Need to write this')

    @classmethod
    def __set_range_point(cls, item, value):
        '''Change the item's stored value to the given value, if necessary.

        This is just an optimization method that keeps item's set_value command
        from being called when it's unnessary.

        Args:
            item (SequenceItem): The item to set.
            value (str or int): The sequence number or path to set the item to.

        '''
        value = cls._conform_to_value(value)

        if value != item.get_value():
            item.set_value(value)

    @classmethod
    def _conform_to_value(cls, value):
        '''Force value into a basic, built-in type.

        Args:
            value (str or int or SequenceItem): The value to convert to an int.

        Returns:
            int: The conformed value.

        '''
        if isinstance(value, six.string_types) and value.isdigit():
            value = int(value)
        elif isinstance(value, cls.get_sequence_item_class()):
            value = value.get_value()

        return value

    def _conform_to_sequence_object(self, value):
        '''Force the value into a rich sequence object.

        Args:
            value (int or str or SequenceItem):
                The information to convert to a sequence object of some kind.

        Returns:
            <sequencer_item.SequenceItem> or NoneType:
                The object given to this function or a new, created instance.

        '''
        def get_item_using_format(format_path, values):
            '''Create a sequence item object using some format path and values.

            This function uses Python's .format() function to make an item.

            Args:
                format_path (str): The Python-formatted path.
                values (list[int]): The values to apply to the format_path.
                                    Other functions expect values to be
                                    sequence paths but this version assumes
                                    that values are integer-items.

            Returns:
                <sequencer_item.SequenceItem> or NoneType:
                    The item created from the base format_path.

            '''
            format_dimensions = len(
                re.findall(conversion.FORMAT_REGEX_STR, format_path))

            if len(values) != format_dimensions:
                return

            try:
                full_path = format_path.format(*values)
            except (ValueError, IndexError):
                return

            return self.get_sequence_item(full_path)

        def get_item_using_path(format_path, value):
            '''Convert a path directly into a sequence item object.

            Args:
                format_path (str): The Python string passed to this function.
                                   Does nothing in this function.
                value (list[str]): Full paths that represent sequence items
                                   for this object.

            Returns:
                <sequencer_item.SequenceItem> or NoneType:
                    The item created from the base format_path.

            '''
            return self.get_sequence_item(value[0])

        def get_item_from_str_value(format_path, value):
            '''Convert string values to ints and make sequence item objects.

            Args:
                format_path (str): The Python-formatted path.
                values (list[str]): Strings that can be converted to integers
                                    and applied to format_path to create a
                                    sequence item.

            Returns:
                <sequencer_item.SequenceItem> or NoneType:
                    The item created from the base format_path.

            '''
            # TODO : Add check to make sure that the string padding is OK
            value = [int(value_) for value_ in value]
            return get_item_using_format(format_path, value)

        if isinstance(value, (self.get_sequence_item_class(), self.__class__)):
            return value

        value = check.force_itertype(value)
        format_path = self.get_format_path()

        strategies = [
            get_item_using_format,
            get_item_using_path,
            get_item_from_str_value,
        ]

        for strategy in strategies:
            item = strategy(format_path, value)
            if item is not None:
                return item

    def _tokenize_sequence_path(self):
        '''tuple[list[str], list[str]]: The non-digit and digit parts.'''
        # /some/path.####.tif -> /some/path.{:04d}.tif
        formatted_string = self.repr_sequence['to_format'](self.template)
        # Remove any inner key info (like 04d) which would cause our next
        # format to fail
        #
        # /some/path.{:04d}.tif -> /some/path.{}.tif
        #
        formatted_string = re.sub('\{[^\{\}]+\}', '{}', formatted_string)

        # /some/path.{}.tif -> ['/some/path.', '.tif']
        non_digit_items = formatted_string.split('{}')

        # /some/path.####.tif -> ['/some/path.', '####', '.tif']
        digit_parts = split_using_subitems(self.template, non_digit_items)

        # ['/some/path.', '####', '.tif'] -> ['####']
        digit_repr_items = [item for item in digit_parts
                            if item not in non_digit_items]

        return (non_digit_items, digit_repr_items)

    def has(self, item):
        '''Check if an object is in this object instance.

        Args:
            value (int or str or SequenceItem):
                The information to check for, in this object instance.
                Any value supported by _conform_to_sequence_object is supported.

        Returns:
            bool: If the current object instance has the given item inside it.

        '''
        item_ = self._conform_to_sequence_object(item)
        was_wrapped = item.__class__ != item_.__class__
        item = item_

        if was_wrapped:
            return item.path in [SequenceAdapter(_item).path for _item in self]
        return item in self

    def has_matching_name(self, sequence):
        '''Check if a sequence represents the same sequence as this object.

        Args:
            sequence (Sequence): The sequence to check.

        Returns:
            bool: If the two sequences's names match.

        '''
        return self.get_format_path() == sequence.get_format_path()

    @classmethod
    def _is_left_of(cls, first, second):
        '''Find if the first sequence is left of the second without overlap.

        Args:
            first (Sequence): The left-most sequence.
            second (Sequence): The right-most sequence.

        Returns:
            bool: If the first sequence is to the left of the second.

        '''
        return first.get_start() < second.get_end() \
            and first.get_end() < second.get_start()

    @classmethod
    def _get_range_point(cls, item, mode):
        '''Get the requested point.

        Depending on if the mode is set to start or end, the returned point may
        be different. If the item is a SequenceItem, it has no start or end so
        its value is retrieved, instead.

        Args:
            item (Sequence or SequenceItem): The object to get the range point.
            mode (str): The return type / value to get.
                        Options are: ('start', 'end', 'real').
                        'real': Returns the original item, not its value.

        Returns:
            int or list[int] or SequenceItem or Sequence:
                The value(s) of the last item. Depending on it mode='real',
                the return object is either some Python built-in type or
                a custom object.

        '''
        def get_end(item):
            '''int or list[int]: The value(s) of the last item.'''
            try:
                return item.get_value()
            except AttributeError:
                pass

            try:
                return item.get_end()
            except AttributeError:
                pass

        def get_start(item):
            '''int or list[int]: The value(s) of the first item.'''
            try:
                return item.get_value()
            except AttributeError:
                pass

            try:
                return item.get_start()
            except AttributeError:
                pass

        mode_options = \
            {
                'end': functools.partial(get_end, item),
                'real': lambda: item,
                'start': functools.partial(get_start, item),
            }
        return mode_options[mode]()

    def fits(self, sequence):
        '''Check if you can place the given sequence inside of this object.

        Args:
            sequence (Sequence): The sequence to check.

        Returns:
            bool: If the given sequence is a subset of this object and
                  the sequences have no overlapping items, return True.

        '''
        is_contained = not self < sequence \
            and not self > sequence \
            and self.overlaps(sequence)

        if not is_contained:
            return False

        for item in sequence:
            if self.contains(item):
                return False

        return True

    def overlaps(self, sequence):
        '''Check if the sequence's name and range are similar to this object.

        Args:
            sequence (Sequence): The sequence to check.

        Returns:
            bool: If the sequence overlaps.

        '''
        return self.values_overlap(sequence) and self.has_matching_name(sequence)

    def values_overlap(self, sequence):
        '''Check if the given sequence's range intersect this object's range.

        Note:
            This method does not care about the names of the sequences.
            /some/sequence1.####.tif (0-20) has overlap with
            /some/sequence2.####.tif (18-24) has overlap, even though they
            aren't the same sequence.

        Args:
            sequence (Sequence): The sequence to check.

        Returns:
            bool: If the sequence overlaps.

        '''
        return not (self < sequence or self > sequence)

    def get_format_path(self):
        '''str: Create a Python-style format string from this sequence.'''
        return self.repr_sequence['to_format'](self.template)

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
        _, digit_parts = self._tokenize_sequence_path()

        if position is None:
            position = range(len(digit_parts))

        position = check.force_itertype(position)

        paddings = []
        for position_ in position:
            paddings.append(digit_parts[position_])

        paddings = tuple(self.repr_sequence['get_value'](padding) for padding in paddings)
        if len(paddings) == 1:
            return paddings[0]
        return paddings

    def get_start_item(self, recursive=False):
        '''SequenceItem or Sequence: The object with the lowest value.'''
        def get_start_recursive(item):
            '''Search this object until a non-Sequence object is returned.'''
            try:
                return get_start_recursive(item.get_start_item())
            except AttributeError:
                return item

        if recursive:
            return get_start_recursive(self.start_item)
        return self.start_item

    def get_dimensions(self):
        '''int: The number of ways that this sequence can increment.'''
        formatted_repr = self.repr_sequence['to_format'](self.template)
        return conversion.get_dimensions(formatted_repr)

    def get_start(self, mode='value', recursive=False):
        '''Get the lowest value of this sequence, or its parent object.

        Note:
            Using mode='real' gives the same value as get_start_item().

        Args:
            mode (:obj:`str`, optional): The mode to use to get the start value.
                'real': Returns the Sequence or SequenceItem assigned to start.
                'value': Returns the value of the start item (usually an int).
                Default: 'value'.

        Returns:
            int or Sequence or SequenceItem:
                Depending on the mode selected, the value may differ.

        '''
        if mode == 'value':
            mode = 'start'

        start_item = self.get_start_item(recursive=recursive)
        return self._get_range_point(start_item, mode)

    def get_end_item(self, recursive=False):
        '''SequenceItem or Sequence: The object with the highest value.'''
        def get_end_recursive(item):
            '''Search this object until a non-Sequence object is returned.'''
            try:
                return get_end_recursive(item.get_end_item())
            except AttributeError:
                return item

        if recursive:
            return get_end_recursive(self.end_item)
        return self.end_item

    def get_end(self, mode='value', recursive=False):
        '''Get the highest value of this sequence, or its parent object.

        Note:
            Using mode='real' gives the same value as get_start_item().

        Args:
            mode (:obj:`str`, optional): The mode to use to get the end value.
                'real': Returns the Sequence or SequenceItem assigned to end.
                'value': Returns the value of the end item (usually an int).
                Default: 'value'.

        Returns:
            int or Sequence or SequenceItem:
                Depending on the mode selected, the value may differ.

        '''
        if mode == 'value':
            mode = 'end'

        end_item = self.get_end_item(recursive=recursive)
        return self._get_range_point(end_item, mode)

    def set_end(self, value):
        '''Change the end of this object to be some value.

        Since the end item is a Sequence or SequenceItem, if value is not
        either class, it will be automatically converted.

        Args:
            value (int or str or SequenceItem or Sequence):
                If value is an int or str, it is converted to a SequenceItem.
                If value is a str, it must be a path that matches this instance.

        '''
        self.__set_range_point(self.get_end_item(recursive=True), value)

    def set_padding(self, value, position=None, force=False):
        '''Change the padding on this sequence to some new value.

        Args:
            value (int or tuple[int]): The value(s) to change padding to.
            position (int or tuple[int]): The padding index(es) to change.
            force (:obj:`bool`, optional):
                If True, the value for this padding will be set, even if it
                may cause this object to break. If False, ValueError will be
                raised, where needed.

        Raises:
            ValueError:
                If force is False and and the padding is less than the max value
                on this sequence, it means that the value would exceed padding
                and break the sequence. An error is raised, instead.

        '''
        max_item_value = max(set(item.get_value() for item in self))
        if not check.is_itertype(max_item_value):
            max_padding = len(str(max_item_value))
        else:
            max_padding = max_item_value

        if not force and value < max_padding:
            raise ValueError(
                'Padding value: "{padding}" is too low. Padding must be at '
                'least "{max_}" because of item, "{item}".'
                ''.format(padding=value, max_=max_padding, item=max_item_value))

        for item in self:
            item.set_padding(value, position)

        non_digit_items, digit_items = self._tokenize_sequence_path()

        if position is None:
            position = list(range(len(digit_items)))

        # Example: If value was 3
        # ['####'] -> ['###']
        #
        for position_ in position:
            digit_items[position_] = self.repr_sequence['make'](value)

        # Join the new non_digit and digit parts together
        new_template = make_alternating_list(non_digit_items, digit_items)
        self.template = ''.join(new_template)

    def set_type(self, as_type, padding=None):
        '''Change the type of this sequence to the given type.

        Args:
            as_type (str):
                The type to change to.
                Options: ('angular', 'dollar_f', 'glob', 'percent', 'hash').
            padding (:obj:`int`, optional):
                If you change from a padding-insensitive type (like glob)
                to one that is padding-sensitive, you must padding to change
                over to. Otherwise, padding is completely optional and just
                functions like set_padding().

        '''
        repr_sequence = conversion.REPR_SEQUENCES[as_type]
        if self.repr_sequence['padding_case'] == 'insensitive' \
                and repr_sequence['padding_case'] == 'sensitive' \
                and padding is None:
            raise ValueError("You must specify a padding when going from a "
                             "type that doesn't care about padding (like glob) "
                             "to another that does (like hash).")

        if repr_sequence['type'] == self.repr_sequence['type']:
            return  # Nothing to do

        # Doesn't matter what the item is, so we just create a fake one
        # based on this object's existing template
        #
        formatted_repr = self.repr_sequence['to_format'](self.template)
        number_of_dimensions = conversion.get_dimensions(formatted_repr)
        fake_values = [0] * number_of_dimensions
        some_item = self.get_sequence_item(formatted_repr.format(*fake_values))

        non_digits = some_item.get_non_digits()

        # '/some/template.####.tif' -> ['/some/path.', '####', '.tif']
        split_items = split_using_subitems(self.template, non_digits)

        # ['/some/path.', '####', '.tif'] -> ['####']
        format_items = [item for item in split_items
                        if self.repr_sequence['is_valid'](item)]

        values = (self.repr_sequence['get_value'](item) for item in format_items)
        values = [value if value is not None else padding for value in values]

        new_digit_items = [repr_sequence['make'](value) for value in values]

        new_template_list = make_alternating_list(non_digits, new_digit_items)
        self.template = ''.join(new_template_list)
        self.repr_sequence = repr_sequence

        if padding is not None:
            self.set_padding(padding)

    def set_start(self, value):
        '''Change the start of this object to be some value.

        Since the start item is a Sequence or SequenceItem, if value is not
        either class, it will be automatically converted.

        Args:
            value (int or str or SequenceItem or Sequence):
                If value is an int or str, it is converted to a SequenceItem.
                If value is a str, it must be a path that matches this instance.

        '''
        self.__set_range_point(self.start_item, value)

    def add_sequence_in_place(self, sequence):
        '''Figure out the best place to add an sequence and then add it.

        Args:
            Sequence: The sequence to add into this sequence.

        '''
        start = sequence.get_start()

        recorded_index = len(self)
        for index, item in enumerate(self):
            if item.get_value() > start:
                recorded_index = index - 1

        self.insert(recorded_index, sequence)

    def add_in_place(self, item):
        '''Find the spot to add the item that will keep a sorted sequence.

        Note:
            The item does not have to fit within the object's range to be valid.
            When an item is added, if its start/end is beyond this object,
            the range of this object will be recalculated.

        Args:
            item (str or int or Sequence or SequenceItem): The item to add.

        Raises:
            ValueError: If the item added is a Sequence and it overlaps
                        this Sequence.

        '''
        item = self._conform_to_sequence_object(item)

        if isinstance(item, self.__class__):
            if self.overlaps(item) and not self.fits(item):
                raise ValueError(
                    '"{cls_}": "{item!r}" cannot be added to object, '
                    '"{obj!r}". Both items overlaps.'.format(
                        cls_=item.__class__.__name__, item=item, obj=self))

            self.add_sequence_in_place(item)
            return

        item_value = item.get_value()

        for index, stored_item in enumerate(list(self)):
            if stored_item.get_value() > item_value:
                self.insert(index, item)
                break
        else:
            self.append(item)

    def append(self, item):
        '''Add the item to the end of the sequence.

        Warning:
            This can break the sequence's sorted items.

        '''
        self.insert(len(self), item)

    def insert(self, position, item):
        '''Add the item to some location in a sequence.

        Warning:
            This can break the sequence's sorted items if you are not careful.
            It's advised to use add_in_place, instead.

        Args:
            position (int): The placement in the stored items to put item.
            item (SequenceItem or Sequence): The item to add to this object.

        '''
        item_ = self._conform_to_sequence_object(item)
        if type(item_) == type(item):
            # If no change was made, make copy of the item
            # We do this so that mutating SequenceItems will not affect other
            # sequences by accident
            #
            item_ = copy.copy(item)

        self.items.insert(position, item_)

        self._recalculate_range()

    def _recalculate_range(self):
        '''Figure out the new range for this sequence based on its items.'''
        items = [SequenceAdapter(item) for item in self.items]
        min_value = min(items, key=operator.methodcaller('get_start'))
        max_value = max(items, key=operator.methodcaller('get_end'))
        self.start_item = min_value.item
        self.end_item = max_value.item

    def as_range(self, mode='real', function=None):
        '''Get back a range of this sequence.

        Args:
            mode (:obj:`str`, optional): The type of range to get.
                'real': Will return the sequence object(s) in this object.
                'flat': If there are sequences in this object, the sequence will
                        be recursed until only SequenceItems remains and only
                        SequenceItems will be returned.
                'bounds': The start and end of this object. It will create and
                          returns for the full sequence, even if the real
                          sequence is missing items.
            function (callable[<sequencer_item.SequenceItem> or Sequence]):
                This function is run right before the sequence object is
                yielded. So, for example, if you want specific information
                about an item, you can add a function to get it, such as
                operator.attrgetter or something.

        Yields:
            SequenceItem or Sequence or object:
                The sequence objects stored in this object.

        '''
        def return_as_is(item):
            '''Give back the passed item, without modifying it.'''
            return item

        def yield_as_is(item):
            '''SequenceItem or Sequence: The item that was passed.'''
            yield item

        def recursive_yield(item):
            '''Search (depth-first) through a Sequence to get all its items.

            Args:
                item (SequenceItem or Sequence): The object to yield or recurse.

            Yields:
                SequenceItem: The item(s) in the sequence.

            '''
            if isinstance(item, self.__class__):
                for inner_item in item:
                    for item_ in recursive_yield(inner_item):
                        yield item_
            else:
                yield item

        def full_range(sequence):
            '''Create and return items for this sequence.

            Note:
                The items returned are based on the range of the sequence.
                If this object has missing elements, this function will yield
                different elements from the actual object (and that's kind of
                the point).

            Yields:
                SequenceItem: The item(s) in the sequence.

            '''
            for item in self._items_iterator(self.get_start('real'),
                                             self.get_end('real')):
                yield item

        if function is None:
            function = return_as_is

        mode_functions = {
            'bounds': full_range,
            'flat': recursive_yield,
            'real': yield_as_is,
        }

        if mode == 'bounds':
            for item in mode_functions[mode](self):
                yield item
        else:
            for item in self.items:
                for item_ in mode_functions[mode](item):
                    yield function(item_)

    def contains(self, item):
        '''Check if the item's path is inside of this object.

        Note:
            This is functionaly different from __contains__ (in). Instead of
            looking for an instance to some item in this object, just the
            paths of item are compared.

            It's like the difference between == and is.

        Args:
            SequenceItem or Sequence: The object that contains a path to check
                                      for in this instance.

        Returns:
            bool: If the item's path was found in this object instance.

        '''
        item_in = item in self
        if item_in:
            return True

        item = self._conform_to_sequence_object(item)

        return item.path in [item_.path for item_ in self]

    def __copy__(self):
        '''Sequence: Make a copy of this instance and return it.'''
        new_item = self.__class__(template=self.template)
        for item in self.as_range('real'):
            new_item.add_in_place(copy.copy(item))

        return new_item

    def __contains__(self, other):
        '''bool: If the exact, given item is in the sequence.'''
        try:
            return other in self.items
        except AttributeError:
            return False

    def __delitem__(self, index):
        '''Delete the item at the given index.

        Args:
            index (int): The position of the sequence to delete.

        '''
        del self.items[index]

    def __eq__(self, other):
        '''Check if the given object has the same start/end as this instance.

        Args:
            other (Sequence): The sequence to check.

        Returns:
            bool: If the objects matches this instance.

        '''
        if not isinstance(other, self.__class__):
            return False

        for current_item, item in itertools.izip(self, other):
            if current_item.path != item.path:
                return False
        return True

    def __gt__(self, other):
        '''bool: Check if the Sequence is later than the current object.'''
        return self._is_left_of(other, self)

    def __lt__(self, other):
        '''bool: Check if the Sequence is earlier than the current object.'''
        return self._is_left_of(self, other)

    def __getitem__(self, index):
        '''Get the sequence object stored at the given index.

        Args:
            index (int): The value to get in the object.

        Returns:
            SequenceItem or Sequence): The item at some index.

        '''
        return self.items[index]

    def __iter__(self):
        '''Iterate over this object and return every item it finds.

        Yields:
            SequenceItem: The items in this sequence.

        '''
        for item in self.as_range('flat'):
            yield item

    def __len__(self):
        '''The number of raw sequence objects in this object.

        Warning:
            This method returns the raw number of objects in this object's items
            to make sure we do not break built-in Python range functionality.

            Do not modify this behavior.

            If you need the number of actual SequenceItems in this object,
            use as_range and then take its length.

        Example:
            >>> seq = Sequence('/something/file.1001.tif', start=10, end=45)
            >>> for index in range(len(seq)):
            >>>     print(sequence[index])

        Returns:
            int: The number of items in this object.

        '''
        return len(self.items)

    def __repr__(self):
        '''str: A description of how to re-create this object, for debugging.'''
        self.INDENT += 1
        has_sequences = False
        reprs = []
        for item in self.as_range('real'):
            if isinstance(item, self.__class__):
                has_sequences = True
            reprs.append(repr(item))

        repr_output = textwrap.dedent(
            '''\
            {cls_}(template={template!r},
                items=[
                    {items},
                ]
            )\
            ''').rstrip()

        for index, item in enumerate(reprs):
            if index == 0:
                reprs[index] = str(item)
            else:
                reprs[index] = textcase.indent(item, '        ' * self.INDENT)

        repr_output = repr_output.format(
            cls_=self.__class__.__name__,
            template=self.template,
            items=',\n'.join(reprs),
        )

        if not has_sequences:
            self.INDENT = 0

        return repr_output

    def __setitem__(self, index, value):
        '''Add the item to some location in a sequence.

        Warning:
            This can break the sequence's sorted items if you are not careful.
            It's advised to use add_in_place, instead.

        Args:
            index (int): The placement in the stored items to put item.
            value (SequenceItem or Sequence): The item to add to this object.

        '''
        self.insert(index, value)

    def __str__(self):
        '''str: Display the items in this object, as a string.'''
        def get_value(item):
            '''int: The value of a SequenceItem.'''
            return item.get_value()

        values = self.as_range('flat', function=get_value)
        value_ranges = grouping.ranges(list(values), return_range=False)

        ranges = []
        for obj in value_ranges:
            if isinstance(obj, int):
                ranges.append(str(obj))
            else:
                try:
                    start, end, step = obj
                except ValueError:
                    start, end = obj
                    step = 1

                range_str = '{start}-{end}'.format(start=start, end=end)
                if step != 1:
                    range_str += 'x{step}'.format(step=step)
                ranges.append(range_str)

        return '{template} [{ranges}]'.format(template=self.template,
                                              ranges=', '.join(ranges))


class SequenceMultiDimensional(Sequence):

    '''An alternative sequence that increments two-dimensionally.

    This class is useful for sequences that have special rules about how
    they are displayed or built, like UDIMs.

    '''

    def __init__(self, template, start=0, end=0):
        '''Create the object with its initial sequence values.

        Warning:
            To make this object easier to init, if only a template and a
            single number is given, it is assumed that the number is meant
            to represent the end, NOT the start.

        Args:
            template (str): The sequence that this object represents.
                Multiple syntaxes are supported for this object.
                For a padding-insensitive sequence, use a glob form
                (example: '/some/sequence.*.tif').
            start (:obj:`int`, optional):
                The beginning of this sequence. Default: 0.
            end (:obj:`int`, optional):
                The end of the sequence. Default: 0.

        '''
        super(SequenceMultiDimensional, self).__init__(
            template=template, start=start, end=end)

    def _items_iterator(self, *args, **kwargs):
        '''<udim_iterator.UdimIterator2D>: The alternate iterator.'''
        return udim_iterator.UdimIterator2D(*args, **kwargs)


class SequenceAdapter(object):

    '''A ghetto class that unifies the different sequence interfaces.'''

    def __init__(self, item):
        '''Create the object and store the given item.

        Args:
            item (SequenceItem or Sequence): The object to adapt.

        '''
        super(SequenceAdapter, self).__init__()
        self.item = item

    @property
    def path(self):
        '''str: The path of this object.'''
        try:
            return self.item.path
        except AttributeError:
            pass

        try:
            return self.item.template
        except AttributeError:
            return ''

    def get_end(self, *args, **kwargs):
        '''int or list[int]: The sequence value.'''
        try:
            return self.item.get_value(*args, **kwargs)
        except AttributeError:
            pass

        try:
            return self.item.get_end(*args, **kwargs)
        except AttributeError:
            pass

    def get_start(self, *args, **kwargs):
        '''int or list[int]: The sequence value.'''
        try:
            return self.item.get_value(*args, **kwargs)
        except AttributeError:
            pass

        try:
            return self.item.get_start(*args, **kwargs)
        except AttributeError:
            pass


def get_sequence_objects(file_paths, sequence_only=True, sort=sorted):
    '''Create sequence objects from raw file paths.

    Args:
        file_paths (list[str]): The paths to convert into sequence objects.
        sequence_only (:obj:`bool`, optional):
            If True, only Sequence classes will be returned. If False,
            Sequence and SequenceItem objects will return. Default is True.
        sort (:obj:`callable[list[str]`, optional):
            A sort strategy for a list of files.
            Default: Python's built-in sorted() method.

    '''
    # TODO : Need to create a way to make unsorted sequences
    file_paths = sort(file_paths)

    sequence_item_objects = collections.defaultdict(list)

    for item_path in file_paths:
        item_object = sequencer_item.SequenceItem(item_path)

        format_digits = []
        for digit_str in item_object.get_digits(as_type=str):
            padding = len(digit_str)
            format_digits.append('{{:0{value}d}}'.format(value=padding))

        padded_format = item_object.get_formatted_path().format(*format_digits)

        sequence_item_objects[padded_format].append(item_path)

    sequences = []
    sequence_collector = dict()
    # TODO : TBD I split these two loops up to make the code more bearable but
    #        it is pretty inefficient. Maybe go back and optimize this, later
    #
    for sequence_format_path, paths in sequence_item_objects.items():
        paths = [sequencer_item.SequenceItem(path) for path in paths]
        hash_path = conversion.to_hash_from_format(sequence_format_path)
        sequence_collector.setdefault(hash_path, dict())
        sequence = None
        for path in paths:
            padding = path.get_padding()
            try:
                # If the sequence is multi-dimensional, we have to convert it
                # to a tuple because lists can't be dict keys
                padding = tuple(padding)
            except TypeError:
                pass

            sequence_collector[hash_path].setdefault(padding, list())
            sequence_collector[hash_path][padding].append(path)

    for path, path_info in sequence_collector.items():
        for padding, items in path_info.items():
            if len(items) < 2:
                if sequence_only:
                    sequence_object = Sequence([items[0].path])
                else:
                    sequence_object = sequencer_item.SequenceItem(path)
            else:
                sequence_object = Sequence(path)
                for item in items:
                    sequence_object.add_in_place(item)

            sequences.append(sequence_object)

    return sequences


def get_sequence_objects_split(*args, **kwargs):
    '''Create and merge all sequences and sequence items in the given file paths.

    Args:
        *args (list): Any args supported by get_sequence_objects_split.
        *kwargs (list): Any args supported by get_sequence_objects_split.

    Returns:
        list[SequenceItem or Sequence]: The created objects.

    '''
    sequences = get_sequence_objects(*args, **kwargs)
    sequence_items = [item for item in sequences
                      if isinstance(item, Sequence.get_sequence_item_class())]
    sequences = [item for item in sequences if isinstance(item, Sequence)]
    return (sequences, sequence_items)


# TODO : This needs tests
def make_sequence(template, *args, **kwargs):
    '''Build a sequence object of some kind, using a template.

    This is a factory method that will find the best sequence class object
    for the given template.

    Args:
        template (str): The sequence. Any format supported by the sequence class
                        is supported by this method.
        *args (list): The information to send to the sequence object,
                      after it initializes.
        *kwargs (dict): The information to send to the sequence object,
                        after it initializes.

    Raises:
        ValueError: If a class for the given template could not be found.

    Returns:
        Sequence or SequenceMultiDimensional: The sequence object to get.

    '''
    repr_sequence = conversion.get_repr_container(template)
    formatted_template = repr_sequence['to_format'](template)
    number_of_dimensions = formatted_template.count('{}')

    if number_of_dimensions == 1:
        return Sequence(template, *args, **kwargs)
    elif number_of_dimensions > 1:
        return SequenceMultiDimensional(template, *args, **kwargs)
    else:
        raise ValueError(
            'Template: "{template}" does not have a supported definition. '
            'Cannot continue.'.format(template=template))


# TODO : Move this to core
def make_alternating_list(list1, list2):
    '''Combine both lists, alternating each of their elements.

    This method will be able to handle varying list lengths.

    Args:
        list1 (list): A list of elements to alternate. This list's 0th index
                      will be the first index of the alternated list.
        list2 (list): A list of elements to alternate.

    Returns:
        list: A list of alternated elements.

    '''
    # TODO : remove this import
    import itertools
    return [element for element in list(itertools.chain.from_iterable(
                [val for val in itertools.izip_longest(list1, list2)]))
            if element != None]


def split_using_subitems(base, subitems, include_subitems=False):
    '''Use a list of items to split some base item.

    This method assumes that every split needed is covered in subitems.
    If subitem doesn't alternate its elements properly or is missing items,
    base will not split properly.

    Todo:
        I tried doing the same thing with re.split but can't figure out why it
        wasn't working. If time, go back and change this to use it.

    Args:
        base (str): The whole string to split. This object, ideally, should have
                    substrings that subitems will identify and use to split it.
        subitems (list[str]): The items that are known to be inside of base
                              and will be used to split up base.
        include_subitems (:obj:`bool`, optional):
            If True, the subitem used to split base will be included in the
            function's return. If False, only the split elements will be
            returned. Default is False.

    Returns:
        list[str]: The split base string.

    '''
    if include_subitems:
        raise NotImplementedError('Need to make include_subitems do something.')

    parts = []
    chunk_to_split = base
    for item in subitems:
        prefix, others = chunk_to_split.split(item, 1)
        chunk_to_split = others
        if prefix:
            parts.append(prefix)
        parts.append(item)

    return parts


if __name__ == '__main__':
    print(__doc__)


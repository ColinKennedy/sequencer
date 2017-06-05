#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''A collection of classes and functions to describe sequences.

Sequences are defined as any continuous elements. The minimum requirement
for a sequence is 3 consecutive items.

'''

# IMPORT STANDARD LIBRARIES
import collections
import functools
import six
import re

# IMPORT THIRD-PARTY LIBRARIES
from six.moves import range

# IMPORT LOCAL LIBRARIES
from . import sequencer_item
from . import udim_iterator
from .core import grouping
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
        def get_format_info_pound(padding, length):
            return ['#' * padding] * length

        def get_format_info_glob(padding, length):
            return ['*'] * length

        super(Sequence, self).__init__()

        if not isinstance(template, six.string_types):
            # assuming these are sequence items, we need to create a valid
            # sequence template for these items, get its range, and create
            # a sequence using that info
            #
            items = [self.get_sequence_item(item) for item in template]
            paddings = [item.get_padding() for item in items]
            has_consistent_padding = all([item.get_padding() for item in items])

            example_item = items[0]

            # Choose the a padding insensitive type or sensitive type
            # (glob vs pound, for example)
            #
            if has_consistent_padding:
                format_info_func = get_format_info_pound
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

        # As a precaution, in case this template is a 2D sequence (like a UDIM)
        # wrap all start/end values into lists
        #
        start = check.force_itertype(start)
        end = check.force_itertype(end)

        self.template = template

        repr_sequence = conversion.get_repr_container(template)
        self.convert_to_format = repr_sequence['to_format']
        self.sequence_type = repr_sequence['type']
        self.padding_sensitive = repr_sequence['padding_case'] == 'sensitive'

        if (not start and not end) or start == end:
            self.items = []
            return

        self.start_item = \
            self.get_sequence_item(
                self.convert_to_format(self.template).format(*start))
        self.end_item = \
            self.get_sequence_item(
                self.convert_to_format(self.template).format(*end))

        self.items = self.get_range_items()

    def get_range_items(self):
        '''list[SequenceItem]: Using this object's start/end, create a range.'''
        range_iterator = self._items_iterator(self.get_start(), self.get_end())
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
        if isinstance(value, (self.get_sequence_item_class(), self.__class__)):
            return value

        value = check.force_itertype(value)

        format_path = self.get_format_path()

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

        strategies = [
            get_item_using_format,
            get_item_using_path,
            get_item_from_str_value,
            ]

        for strategy in strategies:
            item = strategy(format_path, value)
            if item is not None:
                return item

    def has(self, item):
        '''Check if an object is in this object instance.

        Args:
            value (int or str or SequenceItem):
                The information to check for, in this object instance.
                Any value supported by _conform_to_sequence_object is supported.

        Returns:
            bool: If the current object instance has the given item inside it.

        '''
        class SequenceAdapter(object):

            '''A ghetto class that unifies the different sequence interfaces.'''

            def __init__(self, item):
                '''Create the object and store the given item.

                Args:
                    item (SequnceItem or Sequence): The object to adapt.

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

    def is_after(self, sequence):
        '''bool: Check if the Sequence is later than the current object.'''
        return self._is_left_of(sequence, self)

    def is_before(self, sequence):
        '''bool: Check if the Sequence is earlier than the current object.'''
        return self._is_left_of(self, sequence)

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
        return not (self.is_before(sequence) or self.is_after(sequence))

    def overlaps(self, sequence):
        '''Check if the sequence's name and range are similar to this object.

        Args:
            sequence (Sequence): The sequence to check.

        Returns:
            bool: If the sequence overlaps.

        '''
        return self.values_overlap(sequence) and self.has_matching_name(sequence)

    def get_format_path(self):
        '''str: Create a Python-style format string from this sequence.'''
        return self.convert_to_format(self.template)

    def get_start_item(self):
        '''SequenceItem or Sequence: The object with the lowest value.'''
        return self.start_item

    def get_start(self, mode='value'):
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

        start_item = self.get_start_item()
        return self._get_range_point(start_item, mode)

    def get_end_item(self):
        '''SequenceItem or Sequence: The object with the highest value.'''
        return self.end_item

    def get_end(self, mode='value'):
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

        end_item = self.get_end_item()
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
        self.__set_range_point(self.end_item, value)

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

    def fits(self, sequence):
        '''Check if you can place the given sequence inside of this object.

        Args:
            sequence (Sequence): The sequence to check.

        Returns:
            bool: If the given sequence is a subset of this object and
                  the sequences have no overlapping items, return True.

        '''
        is_contained = not self.is_before(sequence) \
            and not self.is_after(sequence) \
            and self.overlaps(sequence)

        if not is_contained:
            return False

        for item in sequence:
            if self.contains(item):
                return False

        return True

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

        if not hasattr(self, 'start_item') or item_value < self.get_start():
            self.set_start(item)
        elif not hasattr(self, 'end_item') or item_value > self.get_end():
            self.set_end(item)

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
        # TODO : Add warning to this method
        item = self._conform_to_sequence_object(item)
        self.items.insert(position, item)

        self._recalculate_range(item)

    def _recalculate_range(self, item=None):
        '''Figure out the new range for this sequence.

        Args:
            item (:obj:`SequenceItem or Sequence`, optional):
                If no item is given to this method, the existing items in the
                sequence will be used to recalculate the start/end. If an item
                is given, its value is used to set the start/end.

        '''
        if item is None:
            self.start_item = min(self, key=lambda item_: item_.get_value())
            self.end_item = max(self, key=lambda item_: item_.get_value())
            return

        if isinstance(item, self.__class__):
            if item.get_end() > self.get_end():
                self.end_item = item
            elif item.get_start() < self.get_start():
                self.start_item = item

            return  # Note: Early return

        item_value = item.get_value()

        if item_value > self.get_end():
            self.end_item = item
        elif item_value < self.get_start():
            self.start_item = item

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
            for item in self._items_iterator(self.get_start(), self.get_end()):
                yield item

        if function is None:
            function = return_as_is

        mode_functions = \
            {
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

    def __contains__(self, other):
        '''bool: If the exact, given item is in the sequence.'''
        return other in self.items

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

        '''
        return isinstance(other, self.__class__) and \
            self.get_start() == other.get_start() and \
            self.get_end() == other.get_end()

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
        return '{cls_}(template={template!r}, start={start}, end={end})' \
            ''.format(cls_=self.__class__.__name__,
                      template=self.template,
                      start=self.get_start(),
                      end=self.get_end())
        # TODO : I need to print items with indentation, recursively

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
        return str(self.items)


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


def get_sequence_objects(file_paths, sort=sorted):
    '''Create sequence objects from raw file paths.

    Args:
        file_paths (list[str]): The paths to convert into sequence objects.
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

    # TODO : TBD I split these two loops up to make the code more bearable but
    #        it is pretty inefficient. Maybe go back and optimize this, later
    #
    for sequence_format_path, paths in sequence_item_objects.items():
        paths = [sequencer_item.SequenceItem(path) for path in paths]
        pound_path = conversion.to_pound_from_format(sequence_format_path)
        sequence = None

        for group in grouping.ranges(
                [path.get_value() for path in paths], return_range=False):
            if isinstance(group, int):
                sequences.append(sequencer_item.SequenceItem(paths[0].path))
                continue

            start_value = group[0]
            end_value = group[1]
            sequence_ = Sequence(pound_path, start_value, end_value)

            if sequence is None:
                sequence = sequence_
            else:
                sequence.add_in_place(sequence_)

        sequences.append(sequence)

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


if __name__ == '__main__':
    print(__doc__)


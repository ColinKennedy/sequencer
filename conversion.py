#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Functions and constants used to convert different sequence representations.

None of these functions depend on a common format (or are very intelligent)
but will convert built-in types without too much work.

'''

# IMPORT STANDARD LIBRARIES
import functools
import glob
import os
import re

# IMPORT THIRD-PARTY LIBRARIES
import six


FORMAT_REGEX_STR = r'\{(?:\w+)?:(\d+)d\}'


def replace_formatted_digits(match):
    '''str: Generate a padded format using the value found in match.'''
    try:
        matched_value = match.group(1)
        if matched_value is None:
            raise AttributeError
    except AttributeError:
        return '{}'
    return '{:0' + str(int(match.group(1))) + 'd}'


def is_dollar_f(path):
    '''bool: If the path is a Houdini-style sequence (some.$F4.tif).'''
    dollar_f_regex = r'\$F(\d+)?'
    return bool(re.search(dollar_f_regex, path))


def make_dollar_f(value):
    '''str: Create a valid dollar-f format item, using value.'''
    return '$F{value}'.format(value=value)


def get_items_dollar_f(path):
    '''list[str]: The items at some dollar path.'''
    def replace_formatted_digits_dollar_f(match):
        r'''str: Convert strings like $F4 and $F to \d{4} and \d.'''
        digits = match.group(1)
        if digits is None:
            return r'\d'
        return r'\d{{val}}'.format(val=digits)

    root_dir, path_base = os.path.split(path)
    dollar_f_regex = r'\$F(\d+)?'
    path_comp = re.sub(
        dollar_f_regex, replace_formatted_digits_dollar_f, path_base)

    return [os.path.join(root_dir, item) for item in os.listdir(root_dir)
            if path_comp.match(item)]


def get_value_dollar_f(item):
    dollar_f_regex = r'\$F(\d+)?'
    return re.match(dollar_f_repr).group(1) or 0


def to_format_dollar_f(path):
    '''str: Convert a Houdini-style path to a Python-format-friendly string.'''
    dollar_f_regex = r'\$F(\d+)?'
    return re.sub(dollar_f_regex, replace_formatted_digits, path)


def is_glob(path):
    '''bool: If the path is a glob sequence (some.*.tif).'''
    return '*' in os.path.basename(path)


def make_glob(value):
    '''str: Create a valid glob format item, using value.'''
    return '*'


def get_items_glob(path):
    '''list[str]: The files located at this glob path (if any).'''
    return glob.glob(path)


def get_value_glob(item):
    return None


def to_format_glob(path):
    '''str: Convert a glob path to a Python-format-friendly string.'''
    return re.sub(r'\*+', '{}', path)


def is_percent(path):
    r'''bool: If the path has a percent-increment style (some.%04d.tif).'''
    return re.search(r'%\d+d', os.path.basename(path))


def make_percent(value):
    '''str: Create a valid percent format item, using value.'''
    return '%{value}d'.format(value=value)


def get_items_percent(path):
    '''list[str]: The file(s)/folder(s) at this percent-style path, if any.'''
    root_path, path_name = os.path.split(path)

    percent_regex = r'(%(\d+)d)'
    found_percents = re.findall(percent_regex, path_name)

    for replace_str, number_of_pounds in found_percents:
        path_name = path_name.replace(replace_str, int(number_of_pounds) * '#')

    return get_items_pound(os.path.join(root_path, path_name))


def get_value_percent(item):
    percent_regex = r'(%(?<value>\d+)d)'
    return re.match(percent_regex, item).group('value') or 0


def to_format_percent(path):
    '''str: Convert a percent-style path to a Python-format-friendly string.'''
    return re.sub(r'%(\d+)d', replace_formatted_digits, path)


def is_pound(path):
    '''bool: If the path is a pound-style syntax (somefile.####.tif).'''
    return '#' in os.path.basename(path)


def make_pound(value):
    '''str: Create a valid pound format item, using value.'''
    return '#' * value


def get_items_pound(path):
    '''list[str]: The file(s)/folder(s) at this pound-style path, if any.'''
    root_dir, path_hash = os.path.split(path)
    path_comp = re.compile(path_hash.replace('#', r'\d'))
    return [os.path.join(root_dir, item) for item in os.listdir(root_dir)
            if path_comp.match(item)]


def get_value_pound(item):
    return item.count('#')


def to_format_from_pound(path):
    '''str: Convert a pound-style path to a Python-format-friendly path.'''
    def replace_with_formatted_digits(match):
        '''str: Generate a padded format using the value found in match.'''
        return '{:0' + str(len(match.group(0))) + 'd}'

    return re.sub('(#+)', replace_with_formatted_digits, path)


def to_pound_from_format(path):
    '''str: Convert a Python-format-friendly to a pound-style path.'''
    def replace_with_pound_characters(match):
        '''str: Create a #### from a matched regex object.'''
        return '#' * int(match.group(1))

    return re.sub(FORMAT_REGEX_STR, replace_with_pound_characters, path)


def get_padding(path):
    '''int: Get the digit's padding, from path.'''
    padding_comp = re.compile(r'(\d+)')
    return len(padding_comp.search(path).group(0))


# TODO : Move this to core
# Reference: http://www.stackoverflow.com/questions/19022686
#
import collections
class ReadOnlyDict(collections.Mapping):

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


# Note: this class hasn't been tested
# Reference: http://www.stackoverflow.com/questions/19022686
#
class ProtectedDict(dict):

    __readonly = False

    def set_readonly(self, allow=1):
        """Allow or deny modifying dictionary"""
        self.__readonly = bool(allow)

    def __setitem__(self, key, value):

        if self.__readonly:
            raise TypeError, "__setitem__ is not supported"
        return dict.__setitem__(self, key, value)

    def __delitem__(self, key):

        if self.__readonly:
            raise TypeError, "__delitem__ is not supported"
        return dict.__delitem__(self, key)


class Delimiter(object):

    '''Custom object to describe the start and end of a path's increment.'''

    def __init__(self, start='', end=''):
        '''Store the characters used for mark an increment.

        Args:
            start (str): The character that notes the increment's start.
            end (str): The character that notes the increment's end.

        Raises:
            ValueError: If the start and end variables are both
                        left undefined.

        '''
        super(Delimiter, self).__init__()

        if start == '' and end == '':
            raise ValueError('You must specify at least one delimiter')

        if start == '' and end != '':
            start = end
        elif end == '' and start != '':
            end = start

        self.start = start
        self.end = end

    @classmethod
    def get_padding_case(cls):
        '''"insensitive": All delimiters are assumed case-unaware.'''
        return 'insensitive'

    def get_type(self):
        '''A unique string to show the delimiter's type and symbols.'''
        return 'delimiter-{sta}{end}'.format(sta=self.start, end=self.end)


def is_angular(self, path):
    '''bool: If the given path's syntax is like 'some.<number>.tif'.'''
    try:
        starting_index = path.index(self.start)
    except (IndexError, ValueError):
        return False

    try:
        ending_index = path.index(self.end)
    except (IndexError, ValueError):
        return False

    return starting_index < ending_index


def make_angular(value):
    '''str: Create a valid angular format item, using value.'''
    return '<fnum>'


def get_items_angular(path):
    '''list[str]: The files at some path of syntax /some/path.<fnum>.tif.'''
    path = re.sub('<.+>', '*', path)
    return glob.glob(path)


def get_value_angular(item):
    return None


def to_format_angular(path):
    '''str: Change a path like /some/path.<f>.tif) to /some/path.{}.tif.'''
    return re.sub('<[^<>]+>', '{}', path)


__ANGULAR_DELIMITER = Delimiter('<', '>')


# The mother container. It controls how every known path type converts
REPR_SEQUENCES = ReadOnlyDict({
    'angular':
        ReadOnlyDict({
            'is_valid': functools.partial(is_angular, __ANGULAR_DELIMITER),
            'get_value': get_value_angular,
            'items': get_items_angular,
            'to_format': to_format_angular,
            'make': make_angular,
            'type': __ANGULAR_DELIMITER.get_type(),
            'padding_case': __ANGULAR_DELIMITER.get_padding_case(),
        }),

    'dollar_f':
        ReadOnlyDict({
            'is_valid': is_dollar_f,
            'get_value': get_value_dollar_f,
            'items': get_items_dollar_f,
            'make': make_dollar_f,
            'to_format': to_format_dollar_f,
            'type': 'dollar_f',
            'padding_case': 'sensitive',
        }),

    'glob':
        ReadOnlyDict({
            'is_valid': is_glob,
            'get_value': get_value_glob,
            'items': get_items_glob,
            'make': make_glob,
            'to_format': to_format_glob,
            'type': 'glob',
            'padding_case': 'insensitive',
        }),

    'percent':
        ReadOnlyDict({
            'is_valid': is_percent,
            'get_value': get_value_percent,
            'items': get_items_percent,
            'make': make_percent,
            'to_format': to_format_percent,
            'type': 'percent',
            'padding_case': 'sensitive',
        }),

    'pound':
        ReadOnlyDict({
            'is_valid': is_pound,
            'get_value': get_value_pound,
            'items': get_items_pound,
            'make': make_pound,
            'to_format': to_format_from_pound,
            'type': 'pound',
            'padding_case': 'sensitive',
        }),
})


def get_repr_container(sequence):
    '''Find the correct methods to process and get information from a sequence.

    This method does not get a sequence's information but gets the methods
    which get that information.

    Args:
        sequence (str): The sequence to get the information of.

    Returns:
        dict[str] or NoneType:
            The functions and 'best' description of this sequence.

    '''
    for repr_type_info in six.itervalues(REPR_SEQUENCES):
        if repr_type_info['is_valid'](sequence):
            return repr_type_info


if __name__ == '__main__':
    print(__doc__)


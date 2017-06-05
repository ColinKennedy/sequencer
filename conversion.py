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


def is_glob(path):
    '''bool: If the path is a glob sequence (some.*.tif).'''
    return '*' in os.path.basename(path)


def get_items_glob(path):
    '''list[str]: The files located at this glob path (if any).'''
    return glob.glob(path)


def to_format_glob(path):
    '''str: Convert a glob path to a Python-format-friendly string.'''
    return re.sub(r'\*+', '{}', path)


def is_percent(path):
    r'''bool: If the path has a percent-increment style (some.%04d.tif).'''
    return re.search(r'%\d+d', os.path.basename(path))


def get_items_percent(path):
    '''list[str]: The file(s)/folder(s) at this percent-style path, if any.'''
    root_path, path_name = os.path.split(path)

    found_percents = re.findall(r'(%(\d+)d)', path_name)

    for replace_str, number_of_pounds in found_percents:
        path_name = path_name.replace(replace_str, int(number_of_pounds) * '#')

    return get_items_pound(os.path.join(root_path, path_name))


def to_format_percent(path):
    '''str: Convert a percent-style path to a Python-format-friendly string.'''
    def replace_formatted_digits(match):
        '''str: Generate a padded format using the value found in match.'''
        return '{:0' + str(int(match.group(1))) + 'd}'

    return re.sub(r'%(\d+)d', replace_formatted_digits, path)


def is_pound(path):
    '''bool: If the path is a pound-style syntax (somefile.####.tif).'''
    return '#' in os.path.basename(path)


def get_items_pound(path):
    '''list[str]: The file(s)/folder(s) at this pound-style path, if any.'''
    root_dir, path_hash = os.path.split(path)
    path_comp = re.compile(path_hash.replace('#', r'\d'))
    return [os.path.join(root_dir, item) for item in os.listdir(root_dir)
            if path_comp.match(item)]


def to_format_from_pound(path):
    '''str: Convert a pound-style path to a Python-format-friendly path.'''
    def replace_with_formatted_digits(match):
        '''str: Generate a padded format using the value found in match.'''
        return '{:0' + str(len(match.group(0))) + 'd}'

    return re.sub('#+', replace_with_formatted_digits, path)


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
        except IndexError:
            return False

        try:
            ending_index = path.index(self.end)
        except IndexError:
            return False

        return starting_index < ending_index

    def get_items_angular(path):
        '''list[str]: The files at some path of syntax /some/path.<fnum>.tif.'''
        path = re.sub('<.+>', '*', path)
        return glob.glob(path)

    def to_format_angular(path):
        '''str: Change a path like /some/path.<f>.tif) to /some/path.{}.tif.'''
        return re.sub('<[^<>]+>', '{}', path)

    angular_delimiter = Delimiter('<', '>')

    # The mother container. It controls how every known path type converts
    repr_sequences = \
        {
            'angular':
            {
                'is_valid': functools.partial(is_angular, angular_delimiter),
                'items': get_items_angular,
                'to_format': to_format_angular,
                'type': angular_delimiter.get_type(),
                'padding_case': angular_delimiter.get_padding_case(),
            },

            'glob':
            {
                'is_valid': is_glob,
                'items': get_items_glob,
                'to_format': to_format_glob,
                'type': 'glob',
                'padding_case': 'insensitive',
            },

            'percent':
            {
                'is_valid': is_percent,
                'items': get_items_percent,
                'to_format': to_format_percent,
                'type': 'percent',
                'padding_case': 'sensitive',
            },

            'pound':
            {
                'is_valid': is_pound,
                'items': get_items_pound,
                'to_format': to_format_from_pound,
                'type': 'pound',
                'padding_case': 'sensitive',
            },
        }

    for repr_type_info in six.itervalues(repr_sequences):
        if repr_type_info['is_valid'](sequence):
            return repr_type_info


if __name__ == '__main__':
    print(__doc__)


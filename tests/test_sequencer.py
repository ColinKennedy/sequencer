#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Tests for sequences, sequence items, and multi dimensional sequences.'''

# IMPORT STANDARD LIBRARIES
import tempfile
import textwrap
import unittest
import shutil
import copy
import os

# IMPORT LOCAL LIBRARIES
from sequencer.sequencer import (Sequence, SequenceMultiDimensional,
                                 get_sequence_objects)
from sequencer.sequencer_item import SequenceItem


ALL_TEMP_FILES_FOLDERS = set()


def clear_temp_files_folders(func):
    '''Run function and delete any temp file(s)/folder(s) it created.

    Args:
        func (callable): The function to wrap and run.

    '''
    def function(*args, **kwargs):
        '''Try to run the function and delete temp location it builds.

        Args:
            *args (list): Any positional args to pass to func.
            *kwargs (list): Any keyword args to pass to func.

        '''
        try:
            return func(*args, **kwargs)
        except:
            raise
        finally:
            for path in set(ALL_TEMP_FILES_FOLDERS):
                remove_cached_path(path)
    return function


# TODO : Make sure to add test cases for when you add a number a UDIM
#        (something with a max width). Make tests for a sequence and and item
#
class ItemMethodTestCase(unittest.TestCase):

    '''Test the methods on a generic SequenceItem object.'''

    def test_dimensions_1d(self):
        '''Test that a generic file is created properly.'''
        item = SequenceItem('/some/path/file.1001.tif')
        self.assertEqual(item.get_dimensions(), 1)

    def test_dimensions_2d(self):
        '''Test that a file with more than one increment strategy inits.'''
        item = SequenceItem('/some/path/file.7.asdfasdfasd.1001.tif')
        self.assertEqual(item.get_dimensions(), 2)
        self.assertEqual(item.get_value(), [7, 1001])

    def test_promote_sequence(self):
        '''Create a sequence from two SequenceItems.'''
        item = SequenceItem('/something/some_file.1001.tif')
        item = item.promote_to_sequence('/something/some_file.1002.tif')
        self.assertTrue(isinstance(item, Sequence))

    def test_promote_sequence_fails_0001(self):
        '''Make sure that incompatible SequenceItems do not make a sequence.'''
        item = SequenceItem('/something/some_file.1001.tif')
        try:
            item.promote_to_sequence('/something/some_file_a.1002.tif')
        except ValueError:
            pass  # This was expected
        else:
            self.assertTrue(False)

    def test_get_padding_implied_position(self):
        '''Request the padding of the only digit in a sequence.'''
        item = SequenceItem('/something/some_file.1001.tif')
        self.assertEqual(item.get_padding(), 4)

    def test_get_padding_explicit_position(self):
        '''Request the padding of the only digit in a sequence, explicitly.'''
        item = SequenceItem('/something/some_file.1001.tif')
        self.assertEqual(item.get_padding(0), 4)

    def test_get_padding_implicit_position_multi(self):
        '''Get the padding of a 2D sequence item, at once.'''
        item = SequenceItem('/something/some_file.100004.1001.tif')
        self.assertEqual(item.get_padding(), (6, 4))

    def test_get_padding_explicit_position_multi(self):
        '''Get the padding of a 2D sequence item, at once.'''
        item = SequenceItem('/something/some_file.100004.1001.tif')
        self.assertEqual(item.get_padding([0, 1]), (6, 4))

    def test_set_value_int(self):
        '''Set the value of SequenceItem with an int.

        The int gets converted to the proper sequence-item-value.

        '''
        item = SequenceItem('/some/path/something.1001.tif')
        item.set_value(1003)
        self.assertEqual(item.get_value(), 1003)
        self.assertEqual(item.path, '/some/path/something.1003.tif')

    def test_set_value_2d_multi(self):
        '''Set all (multiple) values of a SequenceItem, at once.'''
        item = SequenceItem('/some/path/some_u4_v7.tif')
        new_values = [6, 3]
        item.set_value(new_values)
        self.assertEqual(item.get_value(), new_values)

    def test_set_value_2d_single(self):
        '''Set one of the positions of a 2D SequenceItem, individually.'''
        item = SequenceItem('/some/path/some_u4_v7.tif')
        index = 1
        new_value = 2
        item.set_value(new_value, position=index)
        self.assertEqual(item.get_value()[index], new_value)

    def test_set_value_2d_int_failed(self):
        '''Make sure that setting with the wrong values failes properly.'''
        item = SequenceItem('/some/path/some_u4_v7.tif')
        try:
            item.set_value(6)
        except ValueError:
            pass  # This was expected
        else:
            self.assertTrue(False)

    def test_sequence_item_equals_sequence_item(self):
        '''Make sure that two sequence items with equal one another.'''
        sequence_item1 = SequenceItem('/some/path.11.tif')
        sequence_item2 = SequenceItem('/some/path.11.tif')

        self.assertEqual(sequence_item1, sequence_item2)

    def test_sequence_copy(self):
        '''Test that copying a sequence creates an exact replica.'''
        sequence_item = SequenceItem('/some/path.11.tif')
        sequence_item_copy = copy.copy(sequence_item)
        self.assertEqual(sequence_item, sequence_item_copy)


class FileSequenceRepresentationTestCase(unittest.TestCase):

    '''Tests where a sequence's representation type gets changed to another.'''

    def test_convert_angular_to_angular(self):
        '''Change from '/some/path.<fnum>.tif' to '/some/path.<fnum>.tif'.'''
        angular_repr = '/a/path/image_padded.<fnum>.tif'
        sequence = Sequence(angular_repr, start=10, end=20)

        sequence.set_type('angular')

        self.assertEqual(sequence.template, angular_repr)

    def test_convert_angular_to_glob(self):
        '''Change from '/some/path.<fnum>.tif' to '/some/path.*.tif'.'''
        sequence = Sequence('/a/path/image_padded.<fnum>.tif',
                            start=10, end=20)

        sequence.set_type('glob')

        self.assertEqual(sequence.template, '/a/path/image_padded.*.tif')

    def test_convert_angular_to_percent(self):
        '''Change from '/some/path.<fnum>.tif' to '/some/path.%04d.tif'.'''
        sequence = Sequence('/a/path/image_padded.<fnum>.tif',
                            start=10, end=20)

        sequence.set_type('percent', padding=4)

        self.assertEqual(sequence.template, '/a/path/image_padded.%04d.tif')

    def test_convert_angular_to_hash(self):
        '''Change from '/some/path.<fnum>.tif' to '/some/path.####.tif'.'''
        sequence = Sequence('/a/path/image_padded.<fnum>.tif',
                            start=10, end=20)

        sequence.set_type('hash', padding=4)

        self.assertEqual(sequence.template, '/a/path/image_padded.####.tif')

    def test_convert_dollar_f_to_angular(self):
        '''Change from 'some_image,$F3.tif' to 'some_image.<f>.tif'.'''
        sequence = Sequence('/a/path/image_padded.$F3.tif', start=10, end=20)
        sequence.set_type('angular')

        self.assertEqual(sequence.template, '/a/path/image_padded.<fnum>.tif')

    def test_convert_dollar_f_to_glob(self):
        '''Change from 'some_image,$F3.tif' to 'some_image.*.tif'.'''
        sequence = Sequence('/a/path/image_padded.$F3.tif', start=10, end=20)
        sequence.set_type('glob')

        self.assertEqual(sequence.template, '/a/path/image_padded.*.tif')

    def test_convert_dollar_f_to_percent(self):
        '''Change from 'some_image,$F3.tif' to 'some_image.%03d.tif'.'''
        sequence = Sequence('/a/path/image_padded.$F3.tif', start=10, end=20)
        sequence.set_type('percent')

        self.assertEqual(sequence.template, '/a/path/image_padded.%03d.tif')

    def test_convert_dollar_f_to_hash(self):
        '''Change from 'some_image,$F3.tif' to 'some_image.###.tif'.'''
        sequence = Sequence('/a/path/image_padded.$F3.tif', start=10, end=20)
        sequence.set_type('hash')

        self.assertEqual(sequence.template, '/a/path/image_padded.###.tif')

    def test_convert_glob_to_angular(self):
        '''Change from '/some/path.*.tif' to '/some/path.<fnum>.tif'.'''
        sequence = Sequence('/a/path/image_padded.*.tif', start=10, end=20)

        sequence.set_type('angular')

        self.assertEqual(sequence.template, '/a/path/image_padded.<fnum>.tif')

    def test_convert_glob_to_dollar_f(self):
        '''Change from 'some_image.*.tif' to 'some_image.$F4.tif'.'''
        sequence = Sequence('/a/path/image_padded.*.tif', start=10, end=20)
        sequence.set_type('dollar_f', padding=4)

        self.assertEqual(sequence.template, '/a/path/image_padded.$F4.tif')

    def test_convert_glob_to_glob(self):
        '''Change from '/some/path.*.tif' to '/some/path.*.tif'.'''
        glob_repr = '/a/path/image_padded.*.tif'
        sequence = Sequence(glob_repr, start=10, end=20)

        sequence.set_type('glob')

        self.assertEqual(sequence.template, glob_repr)

    def test_convert_glob_to_percent(self):
        '''Change from '/some/path.*.tif' to '/some/path.%04d.tif'.'''
        sequence = Sequence('/a/path/image_padded.*.tif', start=10, end=20)

        sequence.set_type('percent', padding=4)

        self.assertEqual(sequence.template, '/a/path/image_padded.%04d.tif')

    def test_convert_glob_to_hash(self):
        '''Change from '/some/path.*.tif' to '/some/path.####.tif'.'''
        sequence = Sequence('/a/path/image_padded.*.tif', start=10, end=20)

        sequence.set_type('hash', padding=4)

        self.assertEqual(sequence.template, '/a/path/image_padded.####.tif')

    def test_convert_percent_to_angular(self):
        '''Change from '/some/path.%04d.tif' to '/some/path.<fnum>.tif'.'''
        sequence = Sequence('/a/path/image_padded.%04d.tif', start=10, end=20)

        sequence.set_type('angular')

        self.assertEqual(sequence.template, '/a/path/image_padded.<fnum>.tif')

    def test_convert_percent_to_dollar_f(self):
        '''Change from 'some_image,%04d.tif' to 'some_image.$F4.tif'.'''
        sequence = Sequence('/a/path/image_padded.%04d.tif', start=10, end=20)
        sequence.set_type('dollar_f')

        self.assertEqual(sequence.template, '/a/path/image_padded.$F4.tif')

    def test_convert_percent_to_glob(self):
        '''Change from '/some/path.%04d.tif' to '/some/path.*.tif'.'''
        sequence = Sequence('/a/path/image_padded.%04d.tif', start=10, end=20)

        sequence.set_type('glob')

        self.assertEqual(sequence.template, '/a/path/image_padded.*.tif')

    def test_convert_percent_to_percent(self):
        '''Change from '/some/path.%04d.tif' to '/some/path.%04d.tif'.'''
        percent_repr = '/a/path/image_padded.%04d.tif'
        sequence = Sequence(percent_repr, start=10, end=20)

        sequence.set_type('percent')

        self.assertEqual(sequence.template, percent_repr)

    def test_convert_percent_to_hash(self):
        '''Change from '/some/path.%04d.tif' to '/some/path.####.tif'.'''
        sequence = Sequence('/a/path/image_padded.%04d.tif', start=10, end=20)

        sequence.set_type('hash')

        self.assertEqual(sequence.template, '/a/path/image_padded.####.tif')

    def test_convert_hash_to_angular(self):
        '''Change from '/some/path.%04d.tif' to '/some/path.<fnum>.tif'.'''
        sequence = Sequence('/a/path/image_padded.####.tif', start=10, end=20)

        sequence.set_type('angular')

        self.assertEqual(sequence.template, '/a/path/image_padded.<fnum>.tif')

    def test_convert_hash_to_dollar_f(self):
        '''Change from 'some_image,####.tif' to 'some_image.$F4.tif'.'''
        sequence = Sequence('/a/path/image_padded.####.tif', start=10, end=20)
        sequence.set_type('dollar_f')

        self.assertEqual(sequence.template, '/a/path/image_padded.$F4.tif')

    def test_convert_hash_to_glob(self):
        '''Change from '/some/path.####.tif' to '/some/path.*.tif'.'''
        sequence = Sequence('/a/path/image_padded.####.tif', start=10, end=20)

        sequence.set_type('glob')

        self.assertEqual(sequence.template, '/a/path/image_padded.*.tif')

    def test_convert_hash_to_percent(self):
        '''Change from '/some/path.####.tif' to '/some/path.%04d.tif'.'''
        sequence = Sequence('/a/path/image_padded.####.tif', start=10, end=20)

        sequence.set_type('percent')

        self.assertEqual(sequence.template, '/a/path/image_padded.%04d.tif')

    def test_convert_hash_to_percent_0001(self):
        '''Change from '/some/path.####.tif' to '/some/path.%03d.tif'.'''
        sequence = Sequence('/a/path/image_padded.####.tif', start=10, end=20)

        sequence.set_type('percent', padding=3)

        self.assertEqual(sequence.template, '/a/path/image_padded.%03d.tif')

    def test_convert_hash_to_hash(self):
        '''Change from '/some/path.####.tif' to '/some/path.####.tif'.'''
        hash_repr = '/a/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)

        sequence.set_type('hash')

        self.assertEqual(sequence.template, hash_repr)


class SequenceConstructionTestCase(unittest.TestCase):

    '''Test the different ways that sequences can be created.'''

    def setUp(self):
        '''Create some generic start/end ranges and a container.'''
        self.offset = 1001
        self.start = 0
        self.end = 100
        self.sequences = []

    def _make_sequence_range(self, template):
        '''Make a sequence object from some template.

        Args:
            template (str): The sequence representation. It can be a variety of
                            styles.

        Returns:
            <sequencer.Sequence>: The sequence for this template.

        '''
        sequence = Sequence(template, start=self.start, end=self.end)
        self.sequences.append(sequence)
        return sequence

    # def _make_sequence_from_template(self, convert, padding=4):
    #     image_full_path, _ = self._make_padded_image_sequence(padding=padding)
    #     image_path_root, image_template = os.path.split(image_full_path)
    #     sequence_repr = convert(image_template)
    #     return Sequence(os.path.join(image_path_root, sequence_repr))

    # def _make_sequence_from_template(self, start, end, template):
    #     return Sequence(start, end, template)

    # def _make_padded_image_sequence(self, padding=4):
    #     if not padding:
    #         template = 'image_padded.{0}.tif'
    #     else:
    #         template = 'image_padded.{{0:{pad}d}}.tif'.format(pad=padding)

    #     temp_folder = make_and_cache_temp_folder()
    #     images = [os.path.join(temp_folder, template.format(frame + self.offset))
    #               for frame in range(self.sequence_start, self.sequence_end + 1)]
    #     for image_name in images:
    #         open(os.path.join(temp_folder, image_name), 'w').close()

    #     return (os.path.join(temp_folder, template), images)

#     def test_0001_make_sequence_from_files(self):
#         # The files may or may not actually exist, on disk.
#         image_template = '/something/some_file_name.{}.tif'

#         images = [image_template.format(index + 1001) for index in range(20)]
#         images.extend(
#             [image_template.format(index + 1031) for index in range(0, 50, 3)])

#         images = (SequenceItem(image) for image in images)
#         image_value_pair = dict((image.get_value(), image) for image in images))

#         final_sequence = Sequence()
#         groups = grouping.ranges(values, False)
#         for group in groups:
#             if isinstance(group, int):
#                 final_sequence.add_item(image_value_pair[group])
#                 continue

#             final_sequence.add_item(Sequence(group[0], group[1], group[2]))

#     @clear_temp_files_folders
#     def test_0001_image_path_padded(self):
#         '''Create a sequence using a list of existing files.'''
#         _, images = self._make_padded_image_sequence(padding=4)
#         sequence = Sequence(images)
#         self.sequences.append(sequence)

#         self.assertEqual(sequence.get_start() - self.offset, self.sequence_start)
#         self.assertEqual(sequence.get_end() - self.offset, self.sequence_end)

#     @clear_temp_files_folders
#     def test_0001_image_path_not_padded(self):
#         '''Create a sequence of images from a glob expression.'''
#         _, images = self._make_padded_image_sequence(padding=0)
#         sequence = Sequence(images)
#         self.sequences.append(sequence)

#         self.assertEqual(sequence.get_start() - self.offset, self.sequence_start)
#         self.assertEqual(sequence.get_end() - self.offset, self.sequence_end)

    def test_create_empty_sequence(self):
        '''Create a sequence that has nothing in it.'''
        sequence = Sequence('/asdfsa/something.####.tif')
        self.assertEqual(len(sequence), 0)

    # def test_add_range_to_empty_sequence(self):
    #     sequence = Sequence('/some/something.####.tif')

    #     sequence.add_in_place('/some/something.0001.tif')
    #     sequence.add_in_place('/some/something.0002.tif')
    #     sequence.add_in_place('/some/something.0003.tif')

    #     self.assertEqual(sequence.get_start(), 1)
    #     self.assertEqual(sequence.get_end(), 3)

    def test_create_and_mutate_empty_sequence(self):
        '''Start with an empty sequence and fill its values.'''
        sequence = Sequence('/asdfsa/something.####.tif')
        initial_items = len(sequence)

        sequence.add_in_place(10)
        start_end1 = (sequence.get_start(), sequence.get_end())
        sequence.add_in_place(12)
        start_end2 = (sequence.get_start(), sequence.get_end())

        self.assertEqual(start_end1, (10, 10))
        self.assertEqual(start_end2, (10, 12))
        self.assertEqual(initial_items, 0)

    @clear_temp_files_folders
    def test_0001_image_path_repr_angular(self):
        '''Create a sequence from a string like /some/image.<f>.tiff.'''
        angular_repr = '/some/path/image_padded.<fnum>.tif'
        sequence = self._make_sequence_range(angular_repr)

        self.assertEqual(sequence.get_start(), self.start)
        self.assertEqual(sequence.get_end(), self.end)

    # @clear_temp_files_folders
    # def test_0001_image_path_repr_angular_2d(self):
    #     angular_repr = 'some_file_u<u>_v<v>.tif'

    #     sequence = Sequence(angular_repr, start=[0, 0], end=[9, 9])

    #     self.assertEqual(sequence.get_start(), (0, 0))
    #     self.assertEqual(sequence.get_end(), (9, 9))

    @clear_temp_files_folders
    def test_0001_image_path_repr_glob(self):
        '''Create a sequence of images that have no padding.'''
        glob_repr = '/some/path/image_padded.*.tif'
        sequence = self._make_sequence_range(glob_repr)

        self.assertEqual(sequence.get_start(), self.start)
        self.assertEqual(sequence.get_end(), self.end)

    @clear_temp_files_folders
    def test_0001_image_path_repr_percent(self):
        '''Create a sequence from a string like /some/image.%04d.tiff.'''
        percent_repr = '/some/path/image_padded.%04d.tif'
        sequence = self._make_sequence_range(percent_repr)

        self.assertEqual(sequence.get_start(), self.start)
        self.assertEqual(sequence.get_end(), self.end)

    @clear_temp_files_folders
    def test_0001_image_path_repr_hash(self):
        '''Create a sequence from a str like /some/image_sequence.####.tif.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = self._make_sequence_range(hash_repr)

        self.assertEqual(sequence.get_start(), self.start)
        self.assertEqual(sequence.get_end(), self.end)

    def test_0001_image_path_repr_dollar_f(self):
        '''Create a sequence from a str like /some/image_sequence.$F4.tif.'''
        dollar_f_repr = '/some/path/image_padded.$F4.tif'
        sequence = self._make_sequence_range(dollar_f_repr)

        self.assertEqual(sequence.get_start(), self.start)

    def test_production_sequence(self):
        '''Create a sequence from a real production path.'''
        some_sequence = '/jobs/someJob_12351394332/shots/sh01/FYI_090/renders/colin-k/FYI_090_some_information.####.tif'
        sequence = Sequence(some_sequence, start=1001, end=2001)
        self.assertEqual(sequence.get_dimensions(), 1)

    def test_single_item_sequence(self):
        '''Make a pseudo-sequence that is actually just one value.'''
        some_item = '/some/path/image_padded.0010.tif'
        sequence = Sequence(some_item)
        expected_item = SequenceItem('/some/path/image_padded.0010.tif')
        self.assertEqual([10], [item.get_value() for item in sequence])

    # @clear_temp_files_folders
    # def test_0001_image_path_udim_mari(self):
    #     raise NotImplementedError('Need to write this')
    #     # some_path = '/some/path/mari.<'
    #     pass

    # @clear_temp_files_folders
    # def test_0001_image_path_udim_zbrush(self):
    #     raise NotImplementedError('Need to write this')
    #     pass

    # @clear_temp_files_folders
    # def test_0001_image_path_udim_mudbox(self):
    #     raise NotImplementedError('Need to write this')
    #     pass

    # def test_0002_check_sequences_are_the_same(self):
    #     sequence = self.sequences[0]

    #     for other_sequence in sequence[1:]:
    #         # Check to make sure that the sequence bounds are the same
    #         self.assertEqual(sequence.start, other_sequence.start)
    #         self.assertEqual(sequence.end, other_sequence.end)

    # def test_0003_check_sequences_are_the_same(self):
    #     sequence = self.sequences[0]
    #     for other_sequence in sequence[1:]:
    #         self.assertTrue(sequence == other_sequence)


class SequenceMethodTestCase(unittest.TestCase):

    '''Test the methods on the generic Sequence object for behavior.'''

    def setUp(self):
        '''Create some generic start/end points for our tests.'''
        self.start = 0
        self.end = 100

    def test_get_end_item(self):
        '''Check the get_end() method on a regular sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=100)
        self.assertEqual(sequence.get_end(), 100)

    def test_get_end_with_nested_sequence(self):
        '''Check get_end() method on a sequence with a sequence inside it.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=100)
        sequence2 = Sequence(hash_repr, start=101, end=200)
        sequence.add_in_place(sequence2)
        self.assertEqual(sequence.get_end(), 200)

    def test_get_end_sequence_real(self):
        '''Make sure that we can get back a sequence object from get_end().'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=100)
        sequence2 = Sequence(hash_repr, start=101, end=200)
        sequence.add_in_place(sequence2)
        self.assertEqual(sequence.get_end('real'), sequence2)

    def test_get_end_sequence_nested(self):
        '''Check get_end() on a complex, nested sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=100)
        sequence2 = Sequence(hash_repr, start=101, end=200)
        sequence3 = Sequence(hash_repr, start=201, end=250)
        sequence2.add_in_place(sequence3)
        sequence.add_in_place(sequence2)
        self.assertEqual(sequence.get_end(), 250)

    def test_get_padding_single(self):
        '''Get the padding of a single-dimension sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=10)
        self.assertEqual(sequence.get_padding(), 4)

    def test_get_padding_multi_dimension(self):
        '''Get the padding of a 2D (or more) dimension sequence.'''
        hash_repr = '/some/path/image_padded.#####.####.tif'
        sequence = SequenceMultiDimensional(hash_repr, start=(0, 0), end=(10, 10))
        self.assertEqual(sequence.get_padding(), (5, 4))

    def test_set_padding(self):
        '''Change the padding of a sequence object.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=10)
        sequence.set_padding(3)

        expected_items = [
            '/some/path/image_padded.000.tif',
            '/some/path/image_padded.001.tif',
            '/some/path/image_padded.002.tif',
            '/some/path/image_padded.003.tif',
            '/some/path/image_padded.004.tif',
            '/some/path/image_padded.005.tif',
            '/some/path/image_padded.006.tif',
            '/some/path/image_padded.007.tif',
            '/some/path/image_padded.008.tif',
            '/some/path/image_padded.009.tif',
            '/some/path/image_padded.010.tif',
        ]

        self.assertEqual([item.path for item in sequence], expected_items)
        self.assertEqual(sequence.template, '/some/path/image_padded.###.tif')

    def test_set_padding_fail_0001(self):
        '''Fail to set padding because the padding was too low.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=10)

        try:
            sequence.set_padding(1)
        except ValueError:
            pass
        else:
            self.assertFalse(True)

    # def test_set_padding_multi(self):
    #     '''Change the padding of a sequence object.'''
    #     hash_repr = '/some/path/image_padded.####.####.tif'
    #     sequence = Sequence(hash_repr, start=[0, 100], end=[300, 12])
    #     sequence.set_padding(3, position=0)

    #     raise ValueError(list(sequence))
    #     self.assertEqual(sequence.template,
    #                      '/some/path/image_padded.###.####.tif')

    def test_values_overlaps_matching(self):
        '''Two sequences whose ranges intersect at least once.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=0, end=100)
        sequence2 = Sequence(hash_repr, start=20, end=100)
        self.assertTrue(sequence1.values_overlap(sequence2))

    def test_values_overlaps_not_matching_name(self):
        '''Two sequences that intersect values but have mismatching names.

        In this case, it makes sense to say that these sequences have
        no overlap, since they technically aren't equal.

        '''
        sequence1 = Sequence('something.####.tif', start=0, end=100)
        sequence2 = Sequence('something2.####.tif', start=20, end=100)
        self.assertTrue(sequence1.values_overlap(sequence2))

    def test_values_overlaps_not_matching_sequence(self):
        '''Two sequences with matching names have no overlapping values.'''
        sequence1 = Sequence('something.####.tif', start=0, end=100)
        sequence2 = Sequence('something.####.tif', start=120, end=200)
        self.assertFalse(sequence1.values_overlap(sequence2))

    def test_add_sequence_item_object(self):
        '''Add a SequenceItem to an existing Sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=7)

        item = SequenceItem('/some/path/image_padded.0008.tif')
        sequence.add_in_place(item)
        self.assertTrue(item in sequence)

    def test_add_sequence_item_copy(self):
        '''Make sure that items added to sequences are added as copies.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=7)

        item = SequenceItem('/some/path/image_padded.0008.tif')
        sequence.add_in_place(item)

        self.assertFalse(sequence.items[8] is item)

    def test_add_sequence_copy(self):
        '''Make sure that sequences added to sequences are added as copies.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=0, end=7)
        sequence2 = Sequence(hash_repr, start=10, end=15)

        sequence1.add_in_place(sequence2)

        self.assertFalse(sequence1.items[-1] is sequence2)

    # TODO : Write this test
    # def test_add_sequence_item_object_already_exists(self):
    #     raise NotImplementedError('Need to write this test')

    def test_add_sequence_item_object_changes_start(self):
        '''Check if a sequence updates when an added item changes its start.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=12, end=20)

        item = SequenceItem('/some/path/image_padded.0010.tif')
        sequence.add_in_place(item)

        self.assertEqual(sequence.get_start(), 10)

    def test_add_sequence_item_object_changes_end(self):
        '''Check if a sequence updates when an added item changes its end.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=12, end=20)

        item = SequenceItem('/some/path/image_padded.0030.tif')
        sequence.add_in_place(item)

        self.assertEqual(sequence.get_end(), 30)

    def test_add_sequence_object_fails_0001_overlap(self):
        '''Fail adding a sequence to a sequence if their items overlap.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=12, end=20)
        sequence2 = Sequence(hash_repr, start=18, end=24)

        try:
            sequence1.add_in_place(sequence2)
        except ValueError:
            pass  # This was expected
        else:
            self.assertTrue(False)

    def test_sequence_fill_gaps_in_sequence(self):
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=15)
        sequence.set_end(20)
        sequence.fill_gaps()

        expected_sequence = Sequence(
            [
                '/some/path/image_padded.0010.tif',
                '/some/path/image_padded.0011.tif',
                '/some/path/image_padded.0012.tif',
                '/some/path/image_padded.0013.tif',
                '/some/path/image_padded.0014.tif',
                '/some/path/image_padded.0015.tif',
                '/some/path/image_padded.0016.tif',
                '/some/path/image_padded.0017.tif',
                '/some/path/image_padded.0018.tif',
                '/some/path/image_padded.0019.tif',
                '/some/path/image_padded.0020.tif',
            ]
        )
        self.assertEqual(sequence, expected_sequence)

    def test_sequence_fill_gaps_in_empty_sequence_fails(self):
        '''Silently fail to fill gaps if no items were found.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr)
        try:
            sequence.fill_gaps()
        except:
            raised = True
        else:
            raised = False

        self.assertFalse(raised)

    def test_sequence_fill_gaps_in_empty_mutated_sequence(self):
        '''Fill any gaps in a sequence that was once empty.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr)
        sequence.add_in_place(10)
        sequence.add_in_place(20)
        sequence.fill_gaps()

        expected_sequence = Sequence(
            [
                '/some/path/image_padded.0010.tif',
                '/some/path/image_padded.0011.tif',
                '/some/path/image_padded.0012.tif',
                '/some/path/image_padded.0013.tif',
                '/some/path/image_padded.0014.tif',
                '/some/path/image_padded.0015.tif',
                '/some/path/image_padded.0016.tif',
                '/some/path/image_padded.0017.tif',
                '/some/path/image_padded.0018.tif',
                '/some/path/image_padded.0019.tif',
                '/some/path/image_padded.0020.tif',
            ]
        )
        self.assertEqual(sequence, expected_sequence)

    def test_set_start_fill_gaps(self):
        '''Fill any gaps that occur when a new start value is explicitly set.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)
        sequence.set_start(5, fill_gaps=True)
        self.assertTrue(sequence.is_continuous())

    def test_set_end_fill_gaps(self):
        '''Fill any gaps that occur when a new end value is explicitly set.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)
        sequence.set_end(25, fill_gaps=True)
        self.assertTrue(sequence.is_continuous())

    def test_sequence_iteration(self):
        '''Loop over a sequence and get each of its items.

        The functionality should be the same for any sequence, even if the
        sequence contains another sequence.

        Note:
            Changing a sequence's items is not recommended
            (we do it here just for this test).

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=12, end=15)
        sequence2 = Sequence(hash_repr, start=17, end=19)

        sequence1.items.append(sequence2)

        expected_items = \
            ['/some/path/image_padded.0012.tif',
             '/some/path/image_padded.0013.tif',
             '/some/path/image_padded.0014.tif',
             '/some/path/image_padded.0015.tif',
             '/some/path/image_padded.0017.tif',
             '/some/path/image_padded.0018.tif',
             '/some/path/image_padded.0019.tif']

        self.assertEqual([item.path for item in sequence1.as_range('flat')],
                         expected_items)

    def test_sequence_iteration_items(self):
        '''Get the items of a sequence, directly. Not the nested items.

        Note:
            Changing a sequence's items is not recommended
            (we do it here just for this test).

        '''
        hash_repr = '/some/path/image_padded.####.tif'

        sequence1 = Sequence(hash_repr)
        sequence1_items = [
            SequenceItem('/some/path/image_padded.0012.tif'),
            SequenceItem('/some/path/image_padded.0013.tif'),
            SequenceItem('/some/path/image_padded.0014.tif'),
            SequenceItem('/some/path/image_padded.0015.tif')]
        for item in sequence1_items:
            sequence1.items.append(item)

        sequence2 = Sequence(hash_repr)
        sequence2_items = [
            SequenceItem('/some/path/image_padded.0017.tif'),
            SequenceItem('/some/path/image_padded.0018.tif'),
            SequenceItem('/some/path/image_padded.0019.tif')]
        for item in sequence2_items:
            sequence2.items.append(item)

        sequence1.items.append(sequence2)

        expected_items = sequence1_items + [sequence2]

        self.assertEqual(list(sequence1.as_range('real')), expected_items)

    def test_sequence_iteration_value(self):
        '''Get the values of a sequence, in a simple function.'''
        def get_value(item):
            '''int: The value on some item.'''
            return item.get_value()

        hash_repr = '/some/path/image_padded.####.tif'
        start = 10
        end = 21
        sequence = Sequence(hash_repr, start=start, end=end)

        self.assertEqual([index for index in range(start, end + 1)],
                         list(sequence.as_range('flat', function=get_value)))

    def test_sequence_iteration_add(self):
        '''Iterate over a sequence that contains items and another sequence.

        Unlike the previous test, which used items, the method add_in_place
        is the correct way to add to the sequence.

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=12, end=15)
        sequence2 = Sequence(hash_repr, start=17, end=19)

        sequence1.add_in_place(sequence2)

        expected_items = \
            ['/some/path/image_padded.0012.tif',
             '/some/path/image_padded.0013.tif',
             '/some/path/image_padded.0014.tif',
             '/some/path/image_padded.0015.tif',
             '/some/path/image_padded.0017.tif',
             '/some/path/image_padded.0018.tif',
             '/some/path/image_padded.0019.tif']

        self.assertEqual([item.path for item in sequence1.as_range('flat')],
                         expected_items)

    def test_sequence_iteration_flat_nested(self):
        '''Iterate over the sequence with nested sequences, within it.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=12, end=15)
        sequence2 = Sequence(hash_repr, start=17, end=19)
        sequence3 = Sequence(hash_repr, start=20, end=22)

        sequence2.add_in_place(sequence3)
        sequence1.add_in_place(sequence2)

        expected_items = \
            ['/some/path/image_padded.0012.tif',
             '/some/path/image_padded.0013.tif',
             '/some/path/image_padded.0014.tif',
             '/some/path/image_padded.0015.tif',

             '/some/path/image_padded.0017.tif',
             '/some/path/image_padded.0018.tif',
             '/some/path/image_padded.0019.tif',

             '/some/path/image_padded.0020.tif',
             '/some/path/image_padded.0021.tif',
             '/some/path/image_padded.0022.tif']

        self.assertEqual([item.path for item in sequence1.as_range('flat')],
                         expected_items)

    def test_sequence_iteration_dunder_iter_items(self):
        '''Check that the __iter__ method works properly.

        In a generic Sequence, this should return the same result as
        as_range('flat').

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=20, end=22)

        expected_items = \
            ['/some/path/image_padded.0013.tif',
             '/some/path/image_padded.0014.tif',
             '/some/path/image_padded.0015.tif',

             '/some/path/image_padded.0017.tif',
             '/some/path/image_padded.0018.tif',
             '/some/path/image_padded.0019.tif']

        for item in expected_items:
            sequence1.add_in_place(SequenceItem(item))

        expected_items.extend(
            ['/some/path/image_padded.0020.tif',
             '/some/path/image_padded.0021.tif',
             '/some/path/image_padded.0022.tif'])

        iterated_items = [item.path for item in sequence1]
        self.assertEqual(iterated_items, expected_items)

    def test_sequence_set_range_0001(self):
        '''Practice changing the range of a sequence when adding another.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=3, end=9)

        sequence1.add_in_place(sequence2)

        self.assertEqual(sequence1.get_start(), 3)
        self.assertEqual(sequence1.get_end(), 20)

    def test_sequence_contains_sequence_item(self):
        '''Check is sequence contains some SequenceItem.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)

        item = SequenceItem('/some/path/image_padded.0030.tif')
        sequence.add_in_place(item)

        item2 = SequenceItem('/some/path/image_padded.0030.tif')
        self.assertTrue(item2 in sequence)

    def test_sequence_dunder_contains_sequence_item(self):
        '''Test that the dunder __contains__ method, to test for equivalency.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)

        item = SequenceItem('/some/path/image_padded.0030.tif')
        sequence.add_in_place(item)
        item2 = SequenceItem('/some/path/image_padded.0030.tif')

        self.assertTrue(item in sequence)
        self.assertTrue(item2 in sequence)

    def test_add_sequence_object_dunder_contains(self):
        '''Check that a sequence can be found in another sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)

        item = SequenceItem('/some/path/image_padded.0030.tif')
        sequence1.add_in_place(item)

        sequence2 = Sequence(hash_repr, start=21, end=29)
        sequence1.add_in_place(sequence2)

        self.assertTrue(sequence2 in sequence1)

    def test_sequence_check_fits(self):
        '''Test that two sequences can be combined together without overlap.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)

        item = SequenceItem('/some/path/image_padded.0030.tif')
        sequence1.add_in_place(item)

        sequence2 = Sequence(hash_repr, start=21, end=29)
        self.assertTrue(sequence2.fits(sequence1))
        self.assertTrue(sequence1.fits(sequence2))

    def test_add_sequence_object_after(self):
        '''Determine which sequence comes later than the other sequence.

        If the sequence's start/end is greater than the other sequence's
        start/end, it's said to be later.

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=21, end=29)

        self.assertTrue(sequence2 > sequence1)

    def test_add_sequence_object_after_failed(self):
        '''Make sure that > fails if Sequences contain any overlap.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=19, end=29)

        self.assertFalse(sequence2 > sequence1)

    def test_add_sequence_object_before(self):
        '''Determine which sequence comes earlier than the other sequence.

        If the sequence's start/end is greater than the other sequence's
        start/end, it's said to be later.

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=21, end=29)

        self.assertTrue(sequence1 < sequence2)

    def test_add_sequence_object_before_failed(self):
        '''Make sure that < fails if Sequences contain any overlap.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=19, end=29)

        self.assertFalse(sequence1 < sequence2)

    def test_sequence_has_str_path(self):
        '''Check if a string path exists in a sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=100)
        self.assertTrue(sequence.has('/some/path/image_padded.0099.tif'))

    # def test_sequence_has_str_int_padding_sensitive_false(self):
    #     hash_repr = '/some/path/image_padded.####.tif'
    #     sequence = Sequence(hash_repr, start=0, end=100)
    #     self.assertFalse(sequence.has('99'))

    # def test_sequence_has_str_int_padding_sensitive_true(self):
    #     hash_repr = '/some/path/image_padded.####.tif'
    #     sequence = Sequence(hash_repr, start=0, end=100)
    #     self.assertTrue(sequence.has('0099'))

    # def test_sequence_has_int_padding_insensitive(self):
    #     hash_repr = '/some/path/image_padded.####.tif'
    #     sequence = Sequence(hash_repr, start=0, end=100)
    #     self.assertTrue(sequence.has(99))

    # def test_add_sequence_item_str(self):
    #     pass

    def test_add_sequence_item_int(self):
        '''Add an iten to a sequence using only an integer.

        The int gets converted to a valid sequence item path before adding
        it to the sequence.

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=0, end=21)
        sequence.add_in_place(22)

        self.assertTrue(
            SequenceItem('/some/path/image_padded.0022.tif') in sequence)

    def test_add_sequence_item_int_fails_0001(self):
        '''Make sure that items can be added to a sequence and retrieved.'''
        hash_repr = '/some/path/image_padded.####.####.tif'
        sequence = SequenceMultiDimensional(
            hash_repr, start=[0, 0], end=[0, 10])
        sequence.add_in_place([1, 12])

        self.assertFalse(22 in sequence)
        self.assertTrue([0, 7] in sequence)
        self.assertTrue([1, 12] in sequence)

    def test_sequence_contains_str_path(self):
        '''Check if a path lives in a sequence, using only a string.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=22)

        image_path = '/some/path/image_padded.0022.tif'
        self.assertTrue(image_path, sequence)

    def test_sequence_contains_int(self):
        '''Check if an increment lives in a sequence, using just an int.

        The stored increment is actually stored in the sequence as a
        SequenceItem but the point is that our sequence object doesn't care
        about that.

        '''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)
        self.assertTrue(10 in sequence)
        self.assertTrue(20 in sequence)
        self.assertFalse(22 in sequence)

    # def test_add_sequence(self):
    #     pass

    def test_iterate_sequence_discontinuous(self):
        '''Iterate over a sequence that has sparse, disconnected elements.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=35, end=37)
        sequence3 = Sequence(hash_repr, start=40, end=42)

        sequence1.add_in_place(sequence2)
        sequence1.add_in_place(sequence3)

        expected_items = \
            [
                # sequence 1
                '/some/path/image_padded.0010.tif',
                '/some/path/image_padded.0011.tif',
                '/some/path/image_padded.0012.tif',
                '/some/path/image_padded.0013.tif',
                '/some/path/image_padded.0014.tif',
                '/some/path/image_padded.0015.tif',
                '/some/path/image_padded.0016.tif',
                '/some/path/image_padded.0017.tif',
                '/some/path/image_padded.0018.tif',
                '/some/path/image_padded.0019.tif',
                '/some/path/image_padded.0020.tif',

                # sequence 2
                '/some/path/image_padded.0035.tif',
                '/some/path/image_padded.0036.tif',
                '/some/path/image_padded.0037.tif',

                # sequence 3
                '/some/path/image_padded.0040.tif',
                '/some/path/image_padded.0041.tif',
                '/some/path/image_padded.0042.tif'
            ]

        the_created_sequence = [item.path for item in sequence1]
        self.assertEqual(the_created_sequence, expected_items)

    def test_sequence_equals_sequence(self):
        '''Make sure that two sequences with equal items compare the same.'''
        items = [
            '/some/path/image_padded.0010.tif',
            '/some/path/image_padded.0011.tif',
            '/some/path/image_padded.0012.tif',
            '/some/path/image_padded.0013.tif',
            '/some/path/image_padded.0014.tif',
            '/some/path/image_padded.0015.tif',
            '/some/path/image_padded.0016.tif',
            '/some/path/image_padded.0017.tif',
            '/some/path/image_padded.0018.tif',
            '/some/path/image_padded.0019.tif',
            '/some/path/image_padded.0020.tif',
        ]

        sequence1 = Sequence(items)
        sequence2 = Sequence(items)

        self.assertEqual(sequence1, sequence2)

    def test_sequence_copy(self):
        '''Test that copying a sequence creates an exact replica.'''
        items = [
            '/some/path/image_padded.0010.tif',
            '/some/path/image_padded.0011.tif',
            '/some/path/image_padded.0012.tif',
            '/some/path/image_padded.0013.tif',
            '/some/path/image_padded.0014.tif',
            '/some/path/image_padded.0015.tif',
            '/some/path/image_padded.0016.tif',
            '/some/path/image_padded.0017.tif',
            '/some/path/image_padded.0018.tif',
            '/some/path/image_padded.0019.tif',
            '/some/path/image_padded.0020.tif',
        ]

        sequence1 = Sequence(items)
        sequence2 = copy.copy(sequence1)

        self.assertEqual(sequence1, sequence2)

    # # def test_set_end_from_path(self):
    # #     pass

    # def test_get_dimension_1d(self):
    #     pass

    # def test_get_dimension_2d(self):
    #     pass

    # def test_get_dimension_3d(self):
    #     pass


class SequenceObjectPrintingTestCase(unittest.TestCase):

    '''Test to make sure __repr__ and __str__ work, as expected.'''

    def test_str_sequence_item(self):
        '''Test the print of a regular sequence item.'''
        item = SequenceItem('/some/path/image_padded.0001.tif')
        self.assertTrue(str(item), "'/some/path/image_padded.0001.tif'")

    def test_repr_sequence_item(self):
        '''Test the repr of a regular sequence item.'''
        item = SequenceItem('/some/path/image_padded.0001.tif')
        self.assertTrue(repr(item),
                        "SequenceItem('/some/path/image_padded.0001.tif')")

    def test_str_sequence(self):
        '''Test the print of a regular sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)

        self.assertEqual(
            str(sequence), '/some/path/image_padded.####.tif [10-20]')

    def test_str_sequence_discontinuous(self):
        '''Test the print of a sequence that has two broken sequences inside.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=35, end=42)

        sequence1.add_in_place(sequence2)

        self.assertEqual(
            str(sequence1), '/some/path/image_padded.####.tif [10-20, 35-42]')

    def test_str_sequence_complex_0001(self):
        '''Test the print of a sequence with nested and individual elements.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=35, end=42)
        sequence1.add_in_place(sequence2)

        for index in range(22, 34, 2):
            sequence1.add_in_place(index)

        sequence1.add_in_place(100)

        self.assertEqual(
            str(sequence1),
            '/some/path/image_padded.####.tif [10-20, 22-32x2, 35-42, 100]')

    def test_repr_sequence(self):
        '''Test the repr of a regular sequence.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence = Sequence(hash_repr, start=10, end=20)

        expected_output = \
            '''\
            Sequence(template='/some/path/image_padded.####.tif',
                items=[
                    SequenceItem('/some/path/image_padded.0010.tif'),
                    SequenceItem('/some/path/image_padded.0011.tif'),
                    SequenceItem('/some/path/image_padded.0012.tif'),
                    SequenceItem('/some/path/image_padded.0013.tif'),
                    SequenceItem('/some/path/image_padded.0014.tif'),
                    SequenceItem('/some/path/image_padded.0015.tif'),
                    SequenceItem('/some/path/image_padded.0016.tif'),
                    SequenceItem('/some/path/image_padded.0017.tif'),
                    SequenceItem('/some/path/image_padded.0018.tif'),
                    SequenceItem('/some/path/image_padded.0019.tif'),
                    SequenceItem('/some/path/image_padded.0020.tif'),
                ]
            )\
            '''.rstrip()

        expected_output = textwrap.dedent(expected_output)
        self.assertEqual(repr(sequence), expected_output)

    def test_repr_sequence_discontinuous(self):
        '''Test the print of a sequence that has two broken sequences inside.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=35, end=37)

        sequence1.add_in_place(sequence2)

        expected_output = textwrap.dedent(
        '''\
        Sequence(template='/some/path/image_padded.####.tif',
            items=[
                SequenceItem('/some/path/image_padded.0010.tif'),
                SequenceItem('/some/path/image_padded.0011.tif'),
                SequenceItem('/some/path/image_padded.0012.tif'),
                SequenceItem('/some/path/image_padded.0013.tif'),
                SequenceItem('/some/path/image_padded.0014.tif'),
                SequenceItem('/some/path/image_padded.0015.tif'),
                SequenceItem('/some/path/image_padded.0016.tif'),
                SequenceItem('/some/path/image_padded.0017.tif'),
                SequenceItem('/some/path/image_padded.0018.tif'),
                SequenceItem('/some/path/image_padded.0019.tif'),
                SequenceItem('/some/path/image_padded.0020.tif'),
                Sequence(template='/some/path/image_padded.####.tif',
                    items=[
                        SequenceItem('/some/path/image_padded.0035.tif'),
                        SequenceItem('/some/path/image_padded.0036.tif'),
                        SequenceItem('/some/path/image_padded.0037.tif'),
                    ]
                ),
            ]
        )\
        ''').rstrip()

        self.assertEqual(repr(sequence1), expected_output)

    def test_repr_sequence_complex_0001(self):
        '''Test the print of a sequence with nested and individual elements.'''
        hash_repr = '/some/path/image_padded.####.tif'
        sequence1 = Sequence(hash_repr, start=10, end=20)
        sequence2 = Sequence(hash_repr, start=35, end=42)
        sequence1.add_in_place(sequence2)

        for index in range(22, 34, 2):
            sequence1.add_in_place(index)

        sequence1.add_in_place(100)

        expected_output = textwrap.dedent(
        '''\
        Sequence(template='/some/path/image_padded.####.tif',
            items=[
                SequenceItem('/some/path/image_padded.0010.tif'),
                SequenceItem('/some/path/image_padded.0011.tif'),
                SequenceItem('/some/path/image_padded.0012.tif'),
                SequenceItem('/some/path/image_padded.0013.tif'),
                SequenceItem('/some/path/image_padded.0014.tif'),
                SequenceItem('/some/path/image_padded.0015.tif'),
                SequenceItem('/some/path/image_padded.0016.tif'),
                SequenceItem('/some/path/image_padded.0017.tif'),
                SequenceItem('/some/path/image_padded.0018.tif'),
                SequenceItem('/some/path/image_padded.0019.tif'),
                SequenceItem('/some/path/image_padded.0020.tif'),
                SequenceItem('/some/path/image_padded.0022.tif'),
                SequenceItem('/some/path/image_padded.0024.tif'),
                SequenceItem('/some/path/image_padded.0026.tif'),
                SequenceItem('/some/path/image_padded.0028.tif'),
                SequenceItem('/some/path/image_padded.0030.tif'),
                SequenceItem('/some/path/image_padded.0032.tif'),
                Sequence(template='/some/path/image_padded.####.tif',
                    items=[
                        SequenceItem('/some/path/image_padded.0035.tif'),
                        SequenceItem('/some/path/image_padded.0036.tif'),
                        SequenceItem('/some/path/image_padded.0037.tif'),
                        SequenceItem('/some/path/image_padded.0038.tif'),
                        SequenceItem('/some/path/image_padded.0039.tif'),
                        SequenceItem('/some/path/image_padded.0040.tif'),
                        SequenceItem('/some/path/image_padded.0041.tif'),
                        SequenceItem('/some/path/image_padded.0042.tif'),
                    ]
                ),
                SequenceItem('/some/path/image_padded.0100.tif'),
            ]
        )\
        ''').rstrip()

        self.assertEqual(repr(sequence1), expected_output)


class MakeSequenceTestCase(unittest.TestCase):

    '''Test the different ways that we can create sequences.'''

    def test_build_sequences_from_files(self):
        '''Create a sequence from a list of files.

        This list could be from a os.listdir() or some other method.

        '''
        some_file_paths = \
            [
                # a discontinuous sequence
                '/some/path/file_name.1001.tif',
                '/some/path/file_name.1002.tif',
                '/some/path/file_name.1003.tif',
                '/some/path/file_name.1004.tif',

                '/some/path/file_name.1006.tif',
                '/some/path/file_name.1007.tif',
                '/some/path/file_name.1008.tif',

                # a continuous sequence
                '/some/path/another_file_name.001009.tif',
                '/some/path/another_file_name.001010.tif',
                '/some/path/another_file_name.001011.tif',
                '/some/path/another_file_name.001012.tif',

                # another, continuous sequence with a different padding
                '/some/path/another_file_name.1009.tif',
                '/some/path/another_file_name.1010.tif',
                '/some/path/another_file_name.1011.tif',
                '/some/path/another_file_name.1012.tif',

                # a sequence in different directory
                '/some/other/path/another_file_name.1001.tif',
                '/some/other/path/another_file_name.1002.tif',
                '/some/other/path/another_file_name.1003.tif',
                '/some/other/path/another_file_name.1004.tif',

                # a 2D sequence
                '/some/2d/sequence_u3_v6.tif',
                '/some/2d/sequence_u3_v7.tif',
                '/some/2d/sequence_u3_v8.tif',
                '/some/2d/sequence_u3_v9.tif',
                '/some/2d/sequence_u4_v0.tif',
                '/some/2d/sequence_u4_v1.tif',
                '/some/2d/sequence_u4_v2.tif',
                '/some/2d/sequence_u4_v3.tif',
                '/some/2d/sequence_u4_v4.tif',

                # a single item (no sequence)
                '/single/item.1001.tif',
            ]

        sequence_objects = get_sequence_objects(some_file_paths,
                                                sequence_only=False)
        sequences = [item for item in sequence_objects
                     if isinstance(item, Sequence)]
        sequence_items = [item for item in sequence_objects
                          if isinstance(item, SequenceItem)]

        self.assertEqual(len(sequences), 5)
        self.assertEqual(len(sequence_items), 1)

    def test_build_sequence_from_files_adapter(self):
        '''Initialize a Sequence object using only a list of files.'''
        some_file_paths = \
            [
                # a discontinuous sequence
                '/some/path/file_name.1001.tif',
                '/some/path/file_name.1002.tif',
                '/some/path/file_name.1003.tif',
                '/some/path/file_name.1004.tif',
            ]

        sequence = Sequence(some_file_paths)
        item_paths = [item.path for item in sequence]

        self.assertEqual(some_file_paths, item_paths)

    def test_build_sequence_only(self):
        '''Test that all items found will come back as Sequence objects.'''
        some_file_paths = [
            # a discontinuous sequence
            '/some/path/file_name.1001.tif',
            '/some/path/file_name.1002.tif',
            '/some/path/file_name.1003.tif',
            '/some/path/file_name.1004.tif',

            '/some/path/file_name.1006.tif',
            '/some/path/file_name.1007.tif',
            '/some/path/file_name.1008.tif',

            # a continuous sequence
            '/some/path/another_file_name.001009.tif',
            '/some/path/another_file_name.001010.tif',
            '/some/path/another_file_name.001011.tif',
            '/some/path/another_file_name.001012.tif',

            # another, continuous sequence with a different padding
            '/some/path/another_file_name.1009.tif',
            '/some/path/another_file_name.1010.tif',
            '/some/path/another_file_name.1011.tif',
            '/some/path/another_file_name.1012.tif',

            # A single item, which will also be cast to a Sequence
            '/some/path/another_file_name2.0001.tif',
        ]

        sequences = get_sequence_objects(some_file_paths, sequence_only=True)
        self.assertEqual(len(sequences), 4)


# class UdimSequnceSetRangeTestCase(unittest.TestCase):
#     def test_mari_set_range_index(self):
#         udim_sequence = UdimSequence('/something/another.####.tif')
#         udim_sequence.set_start(1001)
#         udim_sequence.set_end(1201)

#         # for udim_path in udim_sequence:
#         #     print(udim_path)

#     def test_mari_set_range_index(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         udim_image.set_end(1101)

#     def test_mari_set_range_invalid(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         try:
#             udim_image.set_end(1100)
#         except ValueError:
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False)

#     def test_mari_set_range_index_no_convert(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         udim_image.set_end(13, convert=False)

#     def test_mari_set_range_index_no_convert_invalid_0001(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         try:
#             udim_image.set_end(-1, convert=False)
#         except ValueError:
#             self.assertTrue(True)

#     def test_fill_missing_files(self):
#         raise NotImplementedError('Need to write this test')

#     def test_add_file(self):
#         raise NotImplementedError('Need to write this')

#     def test_add_file_incorrect_padding(self):
#         raise NotImplementedError('Need to write this')

#     def test_add_file_ignore_padding(self):
#         raise NotImplementedError('Need to write this')

    # def test_get_dimension_1d(self):
    #     pass

    # def test_get_dimension_2d(self):
    #     pass

    # def test_get_dimension_3d(self):
    #     pass


# class UdimSequnceSetRangeTestCase(unittest.TestCase):
#     def test_mari_set_range_index(self):
#         udim_sequence = UdimSequence('/something/another.####.tif')
#         udim_sequence.set_start(1001)
#         udim_sequence.set_end(1201)

#         # for udim_path in udim_sequence:
#         #     print(udim_path)

#     def test_mari_set_range_index(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         udim_image.set_end(1101)

#     def test_mari_set_range_invalid(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         try:
#             udim_image.set_end(1100)
#         except ValueError:
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False)

#     def test_mari_set_range_index_no_convert(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         udim_image.set_end(13, convert=False)

#     def test_mari_set_range_index_no_convert_invalid_0001(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         try:
#             udim_image.set_end(-1, convert=False)
#         except ValueError:
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False)

#     def test_mari_set_range_index_no_convert_invalid_0002(self):
#         raise NotImplementedError('Need to write this')
#         udim_image = UdimSequence()
#         try:
#             udim_image.set_end(2.123, convert=False)
#         except ValueError:
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False)

#     def test_zbrush_set_range_index(self):
#         raise NotImplementedError('Need to write this')
#         pass

#     def test_zbrush_set_range_invalid(self):
#         raise NotImplementedError('Need to write this')
#         try:
#             pass
#         except ValueError:
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False)

#     def test_zbrush_set_range_index_no_convert(self):
#         raise NotImplementedError('Need to write this')
#         pass

#     def test_zbrush_set_range_index_no_convert_invalid(self):
#         raise NotImplementedError('Need to write this')
#         try:
#             pass
#         except ValueError:
#             self.assertTrue(True)
#         else:
#             self.assertTrue(False)


# class UdimSequenceTypeManagementTestCase(unittest.TestCase):
#     def test_convert_from_1_base_to_0(self):
#         pass
#         raise NotImplementedError('Need to write this')


# class GetSequenceTestCase(unittest.TestCase):
#     def test_get_sequence_for_mari_sequence(self):

#         pass

#     def test_get_sequence_for_sequences(self):
#         pass

# def test_build_sequences_of_varying_dimensions(self):
#     '''Auto-determine the right sequence classes needed to make.

#     In the test_build_sequences_from_files test, a bunch of varying sequence
#     input is tested but all of the sequences are the same dimension.

#     Here, we'll make sure that UDIMs will work with regular sequences.

#     '''
#     some_file_paths = \
#         [
#             # a discontinuous sequence. This sequence could be a UDIM
#             # but also could be a file sequence starting at 1001.
#             # Without the 10th index, (Where 1009 becomes 1100) it's
#             # impossible to know. So we assume, in that case, it's just
#             # a regular sequence
#             #
#             '/some/path/file_name.1001.tif',
#             '/some/path/file_name.1002.tif',
#             '/some/path/file_name.1003.tif',
#             '/some/path/file_name.1004.tif',

#             '/some/path/file_name.1006.tif',
#             '/some/path/file_name.1007.tif',
#             '/some/path/file_name.1008.tif',

#             # a continuous sequence
#             '/some/path/another_file_name.001009.tif',
#             '/some/path/another_file_name.001010.tif',
#             '/some/path/another_file_name.001011.tif',
#             '/some/path/another_file_name.001012.tif',

#             # A UDIM, 2D sequence
#             '/some/path/udim_file_name.1001.tif',
#             '/some/path/udim_file_name.1002.tif',
#             '/some/path/udim_file_name.1003.tif',
#             '/some/path/udim_file_name.1004.tif',
#             '/some/path/udim_file_name.1005.tif',
#             '/some/path/udim_file_name.1006.tif',
#             '/some/path/udim_file_name.1007.tif',
#             '/some/path/udim_file_name.1008.tif',
#             '/some/path/udim_file_name.1009.tif',
#             '/some/path/udim_file_name.1101.tif',
#         ]

#     sequence_objects = get_sequence_objects(some_file_paths)
#     sequences = [item for item in sequence_objects
#                  if isinstance(item, Sequence)]
#     sequence_items = [item for item in sequence_objects
#                       if isinstance(item, SequenceItem)]

#     self.assertEqual(len(sequences), 4)
#     self.assertEqual(len(sequence_items), 1)

# def test_sequence_udim_types(self):
#     some_file_paths = [
#         # A Mari UDIM sequence
#         '/some/path/file_name.1001.tif',
#         '/some/path/file_name.1002.tif',
#         '/some/path/file_name.1003.tif',
#         '/some/path/file_name.1004.tif',
#         '/some/path/file_name.1005.tif',
#         '/some/path/file_name.1006.tif',
#         '/some/path/file_name.1007.tif',
#         '/some/path/file_name.1008.tif',
#         '/some/path/file_name.1009.tif',
#         '/some/path/file_name.1101.tif',
#         '/some/path/file_name.1102.tif',
#         '/some/path/file_name.1103.tif',

#         # A Zbrush sequence (which is missing its first index)
#         '/some/path/file_name2_u0_v1.tif'
#         '/some/path/file_name2_u0_v2.tif'
#         '/some/path/file_name2_u0_v3.tif'
#         '/some/path/file_name2_u0_v4.tif'
#         '/some/path/file_name2_u0_v5.tif'
#         '/some/path/file_name2_u0_v6.tif'
#         '/some/path/file_name2_u0_v7.tif'
#         '/some/path/file_name2_u0_v8.tif'
#         '/some/path/file_name2_u0_v9.tif'
#         '/some/path/file_name2_u0_v10.tif'
#         '/some/path/file_name2_u1_v0.tif'
#         '/some/path/file_name2_u1_v2.tif'

#         # A Mudbox sequence (algorithmically, it's impossible to know if
#         # this is a mudbox sequence or a Zbrush sequence that is missing
#         # its first 10 indexes. But we assume it's Mudbox because what
#         # person would not use the first 10 indexes?)
#         #
#         '/some/path/file_name2_u1_v1.tif'
#         '/some/path/file_name2_u1_v2.tif'
#         '/some/path/file_name2_u1_v3.tif'
#         '/some/path/file_name2_u1_v4.tif'
#         '/some/path/file_name2_u1_v5.tif'
#         '/some/path/file_name2_u1_v6.tif'
#         '/some/path/file_name2_u1_v7.tif'
#         '/some/path/file_name2_u1_v8.tif'
#         '/some/path/file_name2_u1_v9.tif'
#         '/some/path/file_name2_u1_v10.tif'
#         '/some/path/file_name2_u2_v0.tif'
#         '/some/path/file_name2_u2_v2.tif'
#     ]


class SequenceMultiDimensionalTestCase(unittest.TestCase):

    '''Test cases for special sequences that have more than one dimension.

    Examples of these would be image tiles, or UDIMs.

    '''

    def test_initialization(self):
        '''Create a multi-dimensional sequence.'''
        SequenceMultiDimensional(
            '/some/path/image_padded_u*_v*.tif',
            start=[0, 0], end=[0, 3])

    def test_udim_sequence_item_set_value_0001(self):
        '''Set the first value of a multi-dimensional sequence item path.

        Example:
            If we have a SequenceItem that is a UDIM, changing the first element
            will change the 'u' value.

        '''
        udim_repr = '/some/path/image_padded_u3_v6.tif'
        udim_image = SequenceItem(udim_repr)
        udim_image.set_value(4, position=0)

        self.assertEqual(udim_image.path, '/some/path/image_padded_u4_v6.tif')

    def test_udim_sequence_item_set_value_0002(self):
        '''Set the second value of a multi-dimensional sequence item path.

        Example:
            If we have a SequenceItem that is a UDIM, changing the second
            element will change the 'u' value.

        '''
        udim_repr = '/some/path/image_padded_u3_v6.tif'
        udim_image = SequenceItem(udim_repr)
        udim_image.set_value(4, position=1)

        self.assertEqual(udim_image.path, '/some/path/image_padded_u3_v4.tif')

    def test_udim_sequence_item_set_value_failed_0001(self):
        '''Fail to set value if it can't match the dimensions on a sequence.'''
        udim_repr = '/some/path/image_padded_u3_v6.tif'
        udim_image = SequenceItem(udim_repr)
        try:
            udim_image.set_value(4)
        except ValueError:
            pass  # This was expected
        else:
            self.assertTrue(False)

    def test_udim_sequence_item_set_multi_value(self):
        '''Set every value on a multi-dimensional sequence item, at once.'''
        udim_repr = '/some/path/image_padded_u3_v6.tif'
        udim_image = SequenceItem(udim_repr)
        udim_image.set_value([0, 1])

        self.assertEqual(udim_image.path, '/some/path/image_padded_u0_v1.tif')

    def test_iteration_flat(self):
        '''Iterate over a UDIM sequence's elements.'''
        sequence = SequenceMultiDimensional(
            '/some/path/image_padded_u*_v*.tif',
            start=[0, 8], end=[1, 1])

        expected_items = \
            [
                '/some/path/image_padded_u0_v8.tif',
                '/some/path/image_padded_u0_v9.tif',
                '/some/path/image_padded_u1_v0.tif',

                '/some/path/image_padded_u1_v1.tif',
            ]

        iterated_items = [item.path for item in sequence]
        self.assertEqual(iterated_items, expected_items)


# class MayaFileSequenceTestCase(unittest.TestCase):
#     def test_image_in_project_folder(self):
#         image_sequence = Sequence()
#         resource = MayaAsset(image_sequence)
#         self.assertTrue(resource.in_expected_folder())
#         raise NotImplementedError('Need to write this')

#     def test_image_not_in_project_subfolder(self):
#         image_sequence = Sequence()
#         resource = MayaAsset(image_sequence)
#         self.assertFalse(resource.in_expected_folder())
#         raise NotImplementedError('Need to write this')

#     def test_image_in_incorrect_project_subfolder(self):
#         image_sequence = Sequence()
#         resource = MayaAsset(image_sequence)
#         self.assertFalse(resource.in_expected_folder())
#         raise NotImplementedError('Need to write this')

#     def test_alembic_in_project_subfolder(self):
#         some_alembic_file = '/some/path/file.abc'
#         resource = MayaAsset(some_alembic_file, asset_type='alembic')
#         self.assertTrue(resource.in_expected_folder())
#         raise NotImplementedError('Need to write this')

#     def test_alembic_in_incorrect_project_subfolder(self):
#         some_alembic_file = '/some/path/file.abc'
#         resource = MayaAsset(some_alembic_file, asset_type='alembic')
#         self.assertFalse(resource.in_expected_folder())
#         raise NotImplementedError('Need to write this')


def make_and_cache_temp_folder(*args, **kwargs):
    '''Create a temp folder and add it to the cache of temp directories.

    Args:
        *args (list): Positional arg values for tempfile.mkdtemp.
        *kwargs (list): Keyword arg values for tempfile.mkdtemp.

    '''
    temp_folder = tempfile.mkdtemp(*args, **kwargs)
    ALL_TEMP_FILES_FOLDERS.add(temp_folder)
    return temp_folder


def remove_cached_path(path):
    '''Remove the path from disk and from the list of temp paths, if it exists.

    Args:
        path (str): The full, absolute path to a folder on disk.

    '''
    if os.path.isdir(path):
        shutil.rmtree(path)

    if path in set(ALL_TEMP_FILES_FOLDERS):
        ALL_TEMP_FILES_FOLDERS.remove(path)


if __name__ == '__main__':
    print(__doc__)


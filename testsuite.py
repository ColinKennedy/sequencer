#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Discover and run the Python test files in this package.'''

# IMPORT STANDARD LIBRARIES
import unittest
import os


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


def discover_and_run():
    '''Look in the tests/test_*.py folder for unittests and run them all.'''
    loader = unittest.TestLoader()
    tests = loader.discover(CURRENT_DIR)
    runner = unittest.TextTestRunner()
    runner.run(tests)


if __name__ == '__main__':
    discover_and_run()


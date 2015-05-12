#!/usr/bin/env python

import sys
import os

if sys.hexversion < 0x02070000:
    import unittest2 as unittest
else:
    import unittest


#set path
TEST_ROOT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(TEST_ROOT)

sys.path.append(PROJECT_ROOT)

#Ensure Django is configured to use our example site
os.environ['DJANGO_SETTINGS_MODULE'] = 'mongoadmin.settings.dev'


#run the tests
tests = unittest.defaultTestLoader.discover(TEST_ROOT, pattern='sites_tests.py')
runner = unittest.TextTestRunner(verbosity=3)
result = runner.run(unittest.TestSuite(tests))

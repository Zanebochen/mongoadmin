#coding: utf-8
"""
 Copied exactly from https://github.com/hmarr/mongoengine/blob/master/mongoengine/django/tests.py

"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'examples.blog.settings'

import unittest
from django.test import TestCase, RequestFactory
from django.conf import settings

from mongoengine import connect


class MongoTestCase(TestCase):
    """
    TestCase class that clear the collection between the tests
    """
    db_name = 'test_%s' % settings.MONGO_DATABASE_NAME

    def __init__(self, methodName='runtest'):
        self.db = connect(self.db_name)
        super(MongoTestCase, self).__init__(methodName)

    def _post_teardown(self):
        super(MongoTestCase, self)._post_teardown()
        self.db.drop_database(self.db_name)

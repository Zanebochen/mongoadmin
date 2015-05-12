#coding: utf-8
from django.test import TestCase
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User


class BaseMongoAdminTests(TestCase):

    def setUp(self):
        self.super_user = User.objects.create_superuser("admin1", "admin@126.com", "password")
        self.user = User.objects.create_user("username", "email@126.com", "password")
        self.factory = RequestFactory()

    def testHasNotViewPermissions(self):
        self.assertTrue(self.client.login(username="username", password="password"))
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 403)

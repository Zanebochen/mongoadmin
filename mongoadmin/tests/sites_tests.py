#coding: utf-8
from django.test import TestCase
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth.models import User, Permission, AnonymousUser

from mongoengine.errors import DoesNotExist

from mongonaut.views import (DocumentAddFormView, DocumentListView,
                             DocumentDetailView, DocumentEditFormView)
from test_blog.models import Post
from test_blog.mongoadmin import PostAdmin


APP_LABEL = 'test_blog'
DOCUMENT_NAME = 'Post'
ADMIN_UINFO = dict(username='admin1', email='admin@126.com', password='password')
NORMAL_UINFO = dict(username='username', email='email@126.com', password='password')
POST_ATTR = dict(title="test_title", content='test_content')


class MongoAdminTests(TestCase):

    post_sql_name = PostAdmin().sql_object.lower()
    com_kwargs = {'app_label': APP_LABEL, 'document_name': DOCUMENT_NAME}
    factory = RequestFactory()

    def setUp(self):
        self.super_user = User.objects.create_superuser(**ADMIN_UINFO)
        self.user = User.objects.create_user(**NORMAL_UINFO)

    def add_permission(self, permission_name):
        # generate permission
        permission = Permission.objects.get_by_natural_key("{0}_{1}".format(permission_name, self.post_sql_name),
                                                           APP_LABEL, self.post_sql_name)
        self.assertNotEqual(permission, None)

        # add permission to user
        self.user.user_permissions.add(permission)

    def post_permission_test(self, url_name, view, user, kwargs={}, status=200):
        """Test whether has Post permission"""
        # generate request
        kwargs.update(self.com_kwargs)
        url_path = reverse(url_name, kwargs=kwargs)

        request = self.factory.get(url_path)
        request.user = user
        response = view.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, status)
        return response

    def post_user_permission_test(self, permission_name,
                                  url_name, view, kwargs={}):
        """normal user permission test. add permission for normal user."""
        self.add_permission(permission_name)
        return self.post_permission_test(url_name, view, self.user, kwargs)

    def post_user_not_permission_test(self, url_name, view, kwargs={}):
        """Test user that has not permission.
        1.normal user who has not be authorized.
        2.Anonymous user.
        """
        self.post_permission_test(url_name, view, self.user, kwargs, status=403)
        anonyous_user = AnonymousUser()
        # not login, redirect to LOGIN_URL
        response = self.post_permission_test(url_name, view, anonyous_user,
                                             kwargs, status=302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))

    def test_has_not_view_any_permissions(self):
        self.assertTrue(self.client.login(**NORMAL_UINFO))
        url_path = reverse('index')
        response = self.client.get(url_path)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        response = self.client.get(url_path)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(url_path))

    def test_has_post_add_permission(self):
        self.post_user_permission_test('add', 'document_detail_add_form',
                                       DocumentAddFormView)
        # super_user
        self.post_permission_test('document_detail_add_form',
                                  DocumentAddFormView, self.super_user)

    def test_has_not_post_add_permission(self):
        self.post_user_not_permission_test('document_detail_add_form',
                                           DocumentAddFormView)

    def test_has_post_listView_permission(self):
        self.post_user_permission_test('view', 'document_list',
                                       DocumentListView)
        # super_user
        self.post_permission_test('document_list', DocumentListView,
                                  self.super_user)

    def test_has_not_post_listView_permission(self):
        self.post_user_not_permission_test('document_list', DocumentListView)

    def test_has_post_detialsView_permission(self):
        post = Post.objects.get_or_create(**POST_ATTR)[0]
        kwargs = {'id': post.id}
        self.post_user_permission_test('view', 'document_detail',
                                       DocumentDetailView, kwargs=kwargs)
        # super_user
        self.post_permission_test('document_detail', DocumentDetailView,
                                  self.super_user, kwargs=kwargs)

    def test_has_not_post_detialsView_permission(self):
        post = Post.objects.get_or_create(**POST_ATTR)[0]
        kwargs = {'id': post.id}
        self.post_user_not_permission_test('document_detail',
                                           DocumentDetailView, kwargs=kwargs)

    def test_has_post_edit_permission(self):
        post = Post.objects.get_or_create(**POST_ATTR)[0]
        kwargs = {'id': post.id}
        self.post_user_permission_test('change', 'document_detail_edit_form',
                                       DocumentEditFormView, kwargs=kwargs)
        # super_user
        self.post_permission_test('document_detail_edit_form',
                                  DocumentEditFormView, self.super_user,
                                  kwargs=kwargs)

    def test_has_not_post_edit_permission(self):
        post = Post.objects.get_or_create(**POST_ATTR)[0]
        kwargs = {'id': post.id}
        self.post_user_not_permission_test('document_detail_edit_form',
                                           DocumentEditFormView, kwargs=kwargs)

    def test_has_post_delete_ermission(self):
        self.assertTrue(self.client.login(**NORMAL_UINFO))
        self.add_permission('delete')
        post = Post.objects.get_or_create(**POST_ATTR)[0]

        kwargs = {'id': post.id}
        kwargs.update(self.com_kwargs)
        url_path = reverse('document_delete', kwargs=kwargs)
        response = self.client.post(url_path)

        self.assertEqual(response.status_code, 302)
        with self.assertRaisesMessage(DoesNotExist, "Post matching query does not exist."):
            Post.objects.get(id=post.id)
        self.client.logout()

        # super_user
        post = Post.objects.get_or_create(**POST_ATTR)[0]
        kwargs = {'id': post.id}
        kwargs.update(self.com_kwargs)
        self.assertTrue(self.client.login(**ADMIN_UINFO))
        url_path = reverse('document_delete', kwargs=kwargs)
        response = self.client.post(url_path)

        self.assertEqual(response.status_code, 302)
        with self.assertRaisesMessage(DoesNotExist, "Post matching query does not exist."):
            Post.objects.get(id=post.id)

    def test_has_not_post_delete_ermission(self):
        # normal user
        self.assertTrue(self.client.login(**NORMAL_UINFO))
        post = Post.objects.get_or_create(**POST_ATTR)[0]
        kwargs = {'id': post.id}
        kwargs.update(self.com_kwargs)
        url_path = reverse('document_delete', kwargs=kwargs)
        response = self.client.post(url_path)
        self.assertEqual(response.status_code, 403)

        # anonymous user.
        self.client.logout()
        response = self.client.post(url_path)
        self.assertEqual(response.status_code, 302)
        # url like: http://testserver/login/?next=/mongoadmin/test_blog/Post/55530417f02ede188891a027/delete/
        self.assertTrue(response.url.endswith(url_path))

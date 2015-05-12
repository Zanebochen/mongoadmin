#coding: utf-8
from django.test import TestCase
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission

from mongoengine.errors import DoesNotExist

from mongonaut.views import (DocumentAddFormView, DocumentListView,
                             DocumentDetailView, DocumentEditFormView)
from test_blog.models import Post
from test_blog.mongoadmin import PostAdmin


APP_LABEL = 'test_blog'
DOCUMENT_NAME = 'Post'
ADMIN_UINFO = dict(username='admin1', email='admin@126.com', password='password')
NORMAL_UINFO = dict(username='username', email='email@126.com', password='password')


class MongoAdminTests(TestCase):

    post_sql_name = PostAdmin().sql_object.lower()
    kwargs = {'app_label': APP_LABEL, 'document_name': DOCUMENT_NAME}

    def setUp(self):
        self.super_user = User.objects.create_superuser(**ADMIN_UINFO)
        self.user = User.objects.create_user(**NORMAL_UINFO)
        self.factory = RequestFactory()

    def test_has_not_view_any_permissions(self):
        self.assertTrue(self.client.login(**NORMAL_UINFO))
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 403)

    def add_permission(self, permission_name):
        # generate permission
        permission = Permission.objects.get_by_natural_key("{0}_{1}".format(permission_name, self.post_sql_name),
                                                           APP_LABEL, self.post_sql_name)
        self.assertNotEqual(permission, None)

        # add permission to user
        self.user.user_permissions.add(permission)

    def post_user_permission_test(self, permission_name,
                                  url_name, view, kwargs={}):
        """normal user permission test"""
        self.add_permission(permission_name)
        return self.post_permission_test(url_name, view, self.user, kwargs)

    def post_permission_test(self, url_name, view, user, kwargs={}):
        # generate request
        kwargs.update(self.kwargs)
        url_path = reverse(url_name, kwargs=kwargs)

        request = self.factory.get(url_path)
        request.user = user
        response = view.as_view()(request, **kwargs)
        self.assertEqual(response.status_code, 200)
        return response

    def test_has_post_add_permission(self):
        self.post_user_permission_test('add', 'document_detail_add_form',
                                       DocumentAddFormView)

    def test_has_post_listView_permission(self):
        self.post_user_permission_test('view', 'document_list',
                                       DocumentListView)

    def test_has_post_detialsView_permission(self):
        post = Post.objects.get_or_create(title="test_title")[0]
        self.post_user_permission_test('view', 'document_detail',
                                       DocumentDetailView, kwargs={'id': post.id})

    def test_has_post_edit_permission(self):
        post = Post.objects.get_or_create(title="test_title")[0]
        self.post_user_permission_test('change', 'document_detail_edit_form',
                                       DocumentEditFormView, kwargs={'id': post.id})

    def test_has_post_delete_ermission(self):
        self.assertTrue(self.client.login(**NORMAL_UINFO))
        self.add_permission('delete')
        post = Post.objects.get_or_create(title="test_title")[0]

        kwargs = {'id': post.id}
        kwargs.update(self.kwargs)
        url_path = reverse('document_delete', kwargs=kwargs)
        response = self.client.post(url_path)

        self.assertEqual(response.status_code, 302)
        with self.assertRaisesMessage(DoesNotExist, "Post matching query does not exist."):
            Post.objects.get(id=post.id)

    def test_super_user_has_permission(self):
        post = Post.objects.get_or_create(title="test_title")[0]
        kwargs = {'id': post.id}

        # add permission
        self.post_permission_test('document_detail_add_form',
                                  DocumentAddFormView, self.super_user)

        # list view permission
        self.post_permission_test('document_list', DocumentListView,
                                  self.super_user)

        # detial view permission
        self.post_permission_test('document_detail', DocumentDetailView,
                                  self.super_user, kwargs=kwargs)

        # edit permission
        self.post_permission_test('document_detail_edit_form',
                                  DocumentEditFormView, self.super_user,
                                  kwargs=kwargs)

        # delete permission
        self.assertTrue(self.client.login(**ADMIN_UINFO))
        kwargs.update(self.kwargs)
        url_path = reverse('document_delete', kwargs=kwargs)
        response = self.client.post(url_path)

        self.assertEqual(response.status_code, 302)
        with self.assertRaisesMessage(DoesNotExist, "Post matching query does not exist."):
            Post.objects.get(id=post.id)

    def test_anonymous_user_permission(self):
        pass

#     def testHasViewPermissionsInvalid(self):
#         self.req.user = DummyUser(is_authenticated=False, is_active=True)
#         self.assertFalse(BaseMongoAdmin().has_view_permission(self.req))
# 
#         self.req.user = DummyUser(is_authenticated=True, is_active=False)
#         self.assertFalse(BaseMongoAdmin().has_view_permission(self.req))
# 
#         self.req.user = DummyUser(is_authenticated=False, is_active=False)
#         self.assertFalse(BaseMongoAdmin().has_view_permission(self.req))
# 
#     def testHasEditPerms(self):
#         self.req.user = DummyUser(is_authenticated=True, is_active=True,
#                                   is_staff=True)
# 
#         self.assertTrue(BaseMongoAdmin().has_edit_permission(self.req))
# 
#     def testHasEditPermsInvalid(self):
#         self.req.user = DummyUser(is_staff=False)
#         self.assertFalse(BaseMongoAdmin().has_edit_permission(self.req))
# 
#         self.req.user = DummyUser(is_active=False)
#         self.assertFalse(BaseMongoAdmin().has_edit_permission(self.req))
# 
#         self.req.user = DummyUser(is_authenticated=False)
#         self.assertFalse(BaseMongoAdmin().has_edit_permission(self.req))
# 
#     def testHasAddPerms(self):
#         self.req.user = DummyUser(is_authenticated=True, is_active=True,
#                                   is_staff=True)
# 
#         self.assertTrue(BaseMongoAdmin().has_add_permission(self.req))
# 
#     def testHasAddPermsInvalid(self):
#         self.req.user = DummyUser(is_staff=False)
#         self.assertFalse(BaseMongoAdmin().has_add_permission(self.req))
# 
#         self.req.user = DummyUser(is_active=False)
#         self.assertFalse(BaseMongoAdmin().has_add_permission(self.req))
# 
#         self.req.user = DummyUser(is_authenticated=False)
#         self.assertFalse(BaseMongoAdmin().has_add_permission(self.req))
# 
#     def testHasDeletPerms(self):
#         self.req.user = DummyUser(is_authenticated=True, is_active=True,
#                                   is_superuser=True)
# 
#         self.assertTrue(BaseMongoAdmin().has_delete_permission(self.req))
# 
#     def testHasDeletePermsInvalid(self):
#         self.req.user = DummyUser(is_superuser=False)
#         self.assertFalse(BaseMongoAdmin().has_delete_permission(self.req))
# 
#         self.req.user = DummyUser(is_active=False, is_superuser=True)
#         self.assertFalse(BaseMongoAdmin().has_delete_permission(self.req))
# 
#         self.req.user = DummyUser(is_authenticated=False, is_superuser=True)
#         self.assertFalse(BaseMongoAdmin().has_delete_permission(self.req))

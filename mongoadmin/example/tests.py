#coding: utf-8
import datetime
import random

from django.test import TestCase
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from example.models import MiccardAnchor


APP_LABEL = 'example'
DOCUMENT_NAME = 'MiccardAnchor'
ADMIN_UINFO = dict(username='admin1', email='admin@126.com', password='password')

NOW = datetime.datetime.now()
NOW_DAY = NOW.strftime("%Y-%m-%d")
NOW_TIME = NOW.strftime("%H:%M:%S")

POST_DATA = {
    'uid': random.randint(10000, 999999999),
    'signtime_0': NOW_DAY,
    'signtime_1': NOW_TIME,
    'gender': random.randint(0, 2),
    'url': 'http://www.test.com',
    'cellphone': 13547894515,
    'admin_time': NOW_TIME,
    'admin_day': NOW_DAY,
    'location_0': u'宁夏',
    'location_1': u'固原市',
    'location_2': u'泾源县',
    # ListField
    'tags_0': 'tags_0',
    'tags_1': 'tags_1',
    'tags_2': 'tags_2',
    # EmbeddedDocumentField
    'middleman_email': 'middleman_email',
    'middleman_user_name': 'middleman_user_name',
    'middleman_created_date_0': NOW_DAY,
    'middleman_created_date_1': NOW_TIME,
    'middleman_is_admin': 'on'
}


class MongoTests(TestCase):

    com_kwargs = {'app_label': APP_LABEL, 'document_name': DOCUMENT_NAME}
    factory = RequestFactory()

    def setUp(self):
        self.super_user = User.objects.create_superuser(**ADMIN_UINFO)
        self.client.login(**ADMIN_UINFO)

    def add_MiccardAnchor(self):
        # Add MiccardAnchor
        url_path = reverse('document_detail_add_form', kwargs=self.com_kwargs)
        response = self.client.post(url_path, POST_DATA)
        self.assertEqual(response.status_code, 302)
        url = response.url
        self.assertTrue(url.startswith('http://testserver/mongoadmin/example/MiccardAnchor/'))

        # 12 bytes ojbect_id
        object_id = url[-25: -1]
        return object_id, url

    def delete_MiccardAnchor(self, object_id):
        # delete MiccardAnchor
        kwargs = {'id': object_id}
        kwargs.update(self.com_kwargs)
        url_path = reverse('document_delete', kwargs=kwargs)
        response = self.client.delete(url_path)
        self.assertTrue(response.status_code, 302)
        self.assertEqual(response.url, 'http://testserver/mongoadmin/example/MiccardAnchor/')

    def test_add_and_delete_MiccardAnchor(self):
        object_id, url = self.add_MiccardAnchor()

        # check document detials
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.delete_MiccardAnchor(object_id)

    def test_edit_MiccardAnchor(self):
        object_id, url = self.add_MiccardAnchor()
        kwargs = {'id': object_id}
        kwargs.update(self.com_kwargs)
        url_path = reverse('document_detail_edit_form', kwargs=kwargs)
        edit_data = POST_DATA.copy()
        edit_data['cellphone'] = 1111111111
        edit_data['uid'] = 77

        response = self.client.post(url_path, data=edit_data)
        anchor = MiccardAnchor.objects.get(uid=77, cellphone=1111111111)
        self.assertTrue(not None, anchor)

        self.delete_MiccardAnchor(object_id)

    def test_multi_search(self):
        objects_list = []
        uid_list = []
        url = ""
        origin_count = MiccardAnchor.objects.count()
        for i in range(5):
            uid = random.randint(10000, 999999999)
            POST_DATA['uid'] = uid
            ojbect_id, url = self.add_MiccardAnchor()
            objects_list.append(ojbect_id)
            uid_list.append(uid)

        uid_list = map(str, uid_list)
        data = {
            'uid': "+".join(uid_list),
            'signtime': NOW_DAY
        }
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)
        # TODO: Test there is 5 rows in response table element.

        # multi delete
        url_path = reverse('document_list', kwargs=self.com_kwargs)
        response = self.client.post(url_path, data={'mongo_id': tuple(objects_list)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(origin_count, MiccardAnchor.objects.count())

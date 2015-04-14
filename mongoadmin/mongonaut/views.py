# -*- coding: utf-8 -*-
"""
TODO move permission checks to the dispatch view thingee
"""
from __future__ import absolute_import

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.forms import Form
from django.views.generic.edit import DeletionMixin, FormView
from django.views.generic import ListView, TemplateView
from django.core.exceptions import ValidationError as django_ValidationError

from mongoengine.django.shortcuts import get_document_or_404
from mongoengine.fields import EmbeddedDocumentField, ListField
from mongoengine.errors import ValidationError as mongo_ValidationError

from .conf import settings
from .forms.forms import MongoModelForm
from .mixins import MongonautFormViewMixin, MongonautViewMixin
from .utils import (log_addition, log_change, log_deletion,
                    is_valid_object_id, get_from_change_data)

import logging
logger = logging.getLogger(__name__)


def get_first_line_doc(content):
    return content.split('\n')[0] if content else ''


class IndexView(MongonautViewMixin, ListView):

    template_name = "mongonaut/index.html"
    queryset = []
    permission = 'has_view_permission'

    def get_queryset(self):
        return self.get_mongoadmins()


class AppListView(MongonautViewMixin, ListView):
    """ :args: <app_label> """

    template_name = "mongonaut/app_list.html"


class DocumentListView(MongonautViewMixin, TemplateView):
    """ :args: <app_label> <document_name>

        TODO - Make a generic document fetcher method
    """
    template_name = "mongonaut/document_list.html"
    permission = 'has_view_permission'
    # permission for delete when get a post request.
    delete_permission = 'has_delete_permission'

    documents_per_page = 20

    def get_permission(self):
        if self.request.method.lower() == "post":
            return self.delete_permission
        else:
            return self.permission

    def get_queryset(self):
        """
        The objects attribute of a Document is actually a QuerySet object.
        This lazily queries the database only when you need the data.
        """
        if hasattr(self, "queryset") and self.queryset is not None:
            return self.queryset

        self.document = getattr(self.models, self.document_name)
        # search. move this to get_queryset
        self.search_str = self.request.GET.get('q')
        self.search_type = self.request.GET.get('select')
        if hasattr(self.mongoadmin, "filterobject"):
            queryset = self.get_filterset(self.request.GET)
            # ordering
            if self.mongoadmin.ordering:
                queryset = queryset.qs.order_by(*self.mongoadmin.ordering)
        else:
            queryset = self.get_qset(self.search_type, self.search_str)
            # ordering
            if self.mongoadmin.ordering:
                queryset = queryset.order_by(*self.mongoadmin.ordering)

        # paging
        queryset = self.process_paging(queryset)

        self.queryset = queryset

        return queryset

    def get_filterset(self, data):
        _data = {}
        self.search_data = None
        for key, value in data.iteritems():
            if key not in self.mongoadmin.filterobject._meta.fields:
                continue

            _data[key] = value

        if _data:
            self.search_data = _data
        queryset = self.mongoadmin.filterobject(data=self.search_data)
        self.obj_count = queryset.count()
        return queryset

    def get_qset(self, select, q):
        queryset = self.document.objects
        if q and select:
            try:
                # 自定义数据转换
                validate_method = getattr(self.document, 'validate_{key}'.format(key=select), None)
                if validate_method:
                    q = validate_method(q)

                mongo_field = getattr(self.document, select, None)
                mongo_field.validate(q)
            except mongo_ValidationError:
                messages.add_message(self.request, messages.ERROR,
                                     u'invalid value:{0}'.format(q))
            except django_ValidationError:
                messages.add_message(self.request, messages.ERROR,
                                     u'invalid value:{0}'.format(q))
            except AttributeError:
                messages.add_message(self.request, messages.ERROR, u'wrong attribute.')
            except Exception as ex:
                messages.add_message(self.request, messages.ERROR, u'system error, please contact admin.')
                logger.error("get_qset error: %s" % (ex, ))
            else:
                params = {}
                if select == 'id':
                    # check to make sure this is a valid ID, otherwise we just continue
                    if is_valid_object_id(q):
                        return queryset.filter(pk=q)
                search_key = "{field}__icontains".format(field=select)
                params[search_key] = q
                queryset = queryset.filter(**params)

        self.obj_count = queryset.count()
        return queryset

    def process_paging(self, queryset):
        ### Start pagination
        ### Note:
        ###    Didn't use the Paginator in Django cause mongoengine querysets are
        ###    not the same as Django ORM querysets and it broke.
        # Make sure page request is an int. If not, deliver first page.
        try:
            self.page = int(self.request.GET.get('page', '1'))
        except ValueError:
            self.page = 1

        self.total_pages = self.obj_count / self.documents_per_page +\
                        (1 if self.obj_count % self.documents_per_page else 0)

        if self.page < 1:
            self.page = 1

        if self.page > self.total_pages:
            self.page = self.total_pages

        start = (self.page - 1) * self.documents_per_page
        end = self.page * self.documents_per_page

        queryset = queryset[start:end] if self.obj_count else queryset

        self.start_index = start

        return queryset

    def get_context_data(self, **kwargs):
        context = super(DocumentListView, self).get_context_data(**kwargs)

        context = self.set_permissions_in_context(context)

        context['object_list'] = self.get_queryset()

        context['document'] = self.document
        context['app_label'] = self.app_label
        context['document_name'] = self.document_name
        context['document_doc'] = get_first_line_doc(self.document.__doc__)
        context['total_count'] = self.obj_count

        # pagination bits
        context['page'] = self.page
        context['documents_per_page'] = self.documents_per_page

        if self.page > 1:
            previous_page_number = self.page - 1
        else:
            previous_page_number = None

        if self.page < self.total_pages:
            next_page_number = self.page + 1
        else:
            next_page_number = None

        context['previous_page_number'] = previous_page_number
        context['has_previous_page'] = previous_page_number is not None
        context['next_page_number'] = next_page_number
        context['has_next_page'] = next_page_number is not None
        context['total_pages'] = self.total_pages
        context['start_index'] = self.start_index

        # Boostrap Select js
        # Search box needs it.
        context['BOOSTRAP_SELECT_JS'] = settings.MONGONAUT_BOOSTRAP_SELECT_JS

        # Part of upcoming list view form functionality
        if self.queryset.count():
            context['keys'] = ['id', ]

            # if empty, add all fileds.
            if not self.mongoadmin.list_fields:
                self.mongoadmin.list_fields = list(self.document._fields_ordered)
                # remove field that should not showed in list.
                for field in self.mongoadmin.exclude_fields:
                    self.mongoadmin.list_fields.remove(field)

            # 完全不在List,Add,Edit中显示, 在model中用作另外的用途.
            fake_list = getattr(self.document, 'fake_list', ())

            # Show those items for which we've got list_fields on the mongoadmin
            for key in [x for x in self.mongoadmin.list_fields if x != 'id' and
                        x in self.document._fields.keys() and
                        x not in fake_list]:

                # TODO - Figure out why this EmbeddedDocumentField and ListField breaks this view
                # Note - This is the challenge part, right? :)
                field = self.document._fields[key]
                if isinstance(field, EmbeddedDocumentField):
                    continue
                if isinstance(field, ListField):
                    continue
                # Primary_key first.
                if field.primary_key:
                    context['keys'].insert(1, key)
                else:
                    context['keys'].append(key)

            # Add some additional operations.
            operations = getattr(self.document, 'operations', {})
            context['operations'] = operations

        if hasattr(self.mongoadmin, 'filterobject'):
            context['search_data'] = self.search_data
            context['has_filters'] = True

        if self.mongoadmin.search_fields:
            context['is_search'] = True
            context['search_fields'] = self.mongoadmin.search_fields
            if self.search_str:
                context['search_str'] = self.search_str
            if self.search_type:
                context['search_type'] = str(self.search_type)

        return context

#     def post(self, request, *args, **kwargs):
#         # TODO - make sure to check the rights of the poster
#         #self.get_queryset() # TODO - write something that grabs the document class better
#         form_class = self.get_form_class()
#         form = self.get_form(form_class)
#         mongo_ids = self.get_initial()['mongo_id']
#         for form_mongo_id in form.data.getlist('mongo_id'):
#             for mongo_id in mongo_ids:
#                 if form_mongo_id == mongo_id:
#                     self.document.objects.get(pk=mongo_id).delete()
# 
#         return self.form_invalid(form)

    def get_all_mongo_ids(self):
        self.query = self.get_queryset()
        mongo_ids = [unicode(x.id) for x in self.query]
        return mongo_ids

    def post(self, request, *args, **kwargs):
        mongo_ids = self.get_all_mongo_ids()
        for form_mongo_id in request.POST.getlist('mongo_id'):
            for mongo_id in mongo_ids:
                if form_mongo_id == mongo_id:
                    self.document.objects.get(pk=mongo_id).delete()
        context = self.get_context_data()
        return self.render_to_response(context)


class DocumentDetailView(MongonautViewMixin, TemplateView):
    """ :args: <app_label> <document_name> <id> """
    template_name = "mongonaut/document_detail.html"
    permission = 'has_view_permission'

    def get_context_data(self, **kwargs):
        context = super(DocumentDetailView, self).get_context_data(**kwargs)
        context = self.set_permissions_in_context(context)
        self.document_type = getattr(self.models, self.document_name)
        self.ident = self.kwargs.get('id')
        self.document = get_document_or_404(self.document_type.objects, pk=self.ident)

        context['document'] = self.document
        context['app_label'] = self.app_label
        context['document_name'] = self.document_name
        context['document_doc'] = get_first_line_doc(self.document.__doc__)
        context['keys'] = ['id', ]
        context['embedded_documents'] = []
        context['list_fields'] = []
        for key in  self.document._fields_ordered:
            if 'id' == key:
                continue
            # TODO - Figure out why this EmbeddedDocumentField and ListField breaks this view
            # Note - This is the challenge part, right? :)
            if isinstance(self.document._fields[key], EmbeddedDocumentField):
                # 处理内嵌文档
                embedded_field = self.document[key]
                doc = embedded_field.__doc__
                embedded_dict = dict(field=embedded_field,
                                     name=doc.split('\n')[0] if doc else key,
                                     keys=embedded_field._fields.keys())
                context['embedded_documents'].append(embedded_dict)
                continue
            if isinstance(self.document._fields[key], ListField):
                context['list_fields'].append(key)
                continue
            context['keys'].append(key)
        return context


class DocumentEditFormView(MongonautViewMixin, FormView, MongonautFormViewMixin):
    """ :args: <app_label> <document_name> <id> """

    template_name = "mongonaut/document_edit_form.html"
    form_class = Form
    success_url = '/'
    permission = 'has_edit_permission'

    def get_success_url(self):
        if self.form.changed_data:
            # 记录修改数据
            change_datas = get_from_change_data(self.form)
            messages = u",,".join("{0}:{1}".format(k, v) for k, v in change_datas.items())
            log_change(self.request, self.document, self.app_label, messages)

        return reverse('document_detail_edit_form', kwargs={'app_label': self.app_label, 'document_name': self.document_name, 'id': self.kwargs.get('id')})

    def get_context_data(self, **kwargs):
        context = super(DocumentEditFormView, self).get_context_data(**kwargs)
        context = self.set_permissions_in_context(context)
        self.document_type = getattr(self.models, self.document_name)

        # Jquery validation js CDN_URL
        context['JQUERY_VALIDATE_JS'] = settings.MONGONAUT_JQUERY_VALIDATE_JS

        if hasattr(self.document.mongoadmin, 'show_in_edit'):
            context['show_in_edit'] = self.document.mongoadmin.show_in_edit
        context['document'] = self.document
        context['app_label'] = self.app_label
        context['document_name'] = self.document_name
        context['document_doc'] = get_first_line_doc(self.document.__doc__)
        context['form_action'] = reverse('document_detail_edit_form', args=[self.kwargs.get('app_label'),
                                                                            self.kwargs.get('document_name'),
                                                                            self.kwargs.get('id')])

        return context

    def get_form(self, Form):
        self.document_type = getattr(self.models, self.document_name)
        self.ident = self.kwargs.get('id')
        self.document = get_document_or_404(self.document_type.objects, pk=self.ident)
        self.form = Form()

        if self.request.method == 'POST':
            # New data.
            self.form = self.process_post_form(u'修改已被保存.', is_save=False)
        else:
            self.form = MongoModelForm(model=self.document_type, instance=self.document).get_form()
        return self.form


class DocumentAddFormView(MongonautViewMixin, FormView, MongonautFormViewMixin):
    """ :args: <app_label> <document_name> <id> """

    template_name = "mongonaut/document_add_form.html"
    form_class = Form
    success_url = '/'
    permission = 'has_add_permission'

    def get_success_url(self):
        log_addition(self.request, self.new_document, self.app_label)
        return reverse('document_detail', kwargs={'app_label': self.app_label, 'document_name': self.document_name, 'id': str(self.new_document.id)})

    def get_context_data(self, **kwargs):
        """ TODO - possibly inherit this from DocumentEditFormView. This is same thing minus:
            self.ident = self.kwargs.get('id')
            self.document = get_document_or_404(self.document_type.objects, pk=self.ident)
        """
        context = super(DocumentAddFormView, self).get_context_data(**kwargs)

        context = self.set_permissions_in_context(context)
        self.document_type = getattr(self.models, self.document_name)

        # Jquery validation js CDN_URL
        context['JQUERY_VALIDATE_JS'] = settings.MONGONAUT_JQUERY_VALIDATE_JS

        context['app_label'] = self.app_label
        context['document_name'] = self.document_name
        context['document_doc'] = get_first_line_doc(self.document_type.__doc__)
        context['form_action'] = reverse('document_detail_add_form', args=[self.kwargs.get('app_label'),
                                                                           self.kwargs.get('document_name')])

        return context

    def get_form(self, Form):
        self.document_type = getattr(self.models, self.document_name)
        self.form = Form()

        if self.request.method == 'POST':
            self.form = self.process_post_form(u'数据已成功保存.')
        else:
            self.form = MongoModelForm(model=self.document_type).get_form()
        return self.form


class DocumentDeleteView(DeletionMixin, MongonautViewMixin, TemplateView):
    """ :args: <app_label> <document_name> <id>

        TODO - implement a GET view for confirmation
    """

    success_url = "/"
    template_name = "mongonaut/document_delete.html"

    def get_success_url(self):
        log_deletion(self.request, self.object, self.app_label)
        messages.add_message(self.request, messages.INFO, u'数据已被删除.')
        return reverse('document_list', kwargs={'app_label': self.app_label, 'document_name': self.document_name})

    def get_object(self):
        self.document_type = getattr(self.models, self.document_name)
        self.ident = self.kwargs.get('id')
        self.document = get_document_or_404(self.document_type.objects, pk=self.ident)
        return self.document

from django.views.decorators.http import require_GET
from django.http.response import HttpResponse
from django.utils.importlib import import_module
from django import http
import json


@require_GET
def DocumentOperation(request, app_label, document_name, id, func_name):
    """trigger the operation that the models defined.
    @return:
        - status, boolean: whether the operation is done normally.
        - on_end, str or None: decide how to do when it is done.
            `None`: no action.
            `refresh`: refresh page.
            `new_url`: goto the new page.
    """

    response = {'status': False,
                'on_end': None}
    # import the models file
    models_name = "{0}.models".format(app_label)
    try:
        models = import_module(models_name)
    except ImportError:
        raise http.Http404('No module name {0}.'.format(models_name))

    document = getattr(models, document_name)
    instance = get_document_or_404(document.objects, pk=id)
    func = getattr(instance, func_name, None)
    try:
        if callable(func):
            on_end = func()
            response['on_end'] = on_end
    except Exception:
        logger.error('operation failed!', exc_info=True)
    else:
        response['status'] = True

    return HttpResponse(json.dumps(response),
                        status=200,
                        content_type="application/json")

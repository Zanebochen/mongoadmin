# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.forms import FileField
from django.http import HttpResponseForbidden
from django.utils.importlib import import_module
from django.utils.decorators import method_decorator
from django import http

from mongoengine.errors import NotUniqueError
from mongoengine.fields import EmbeddedDocumentField

from .conf import settings
from .exceptions import NoMongoAdminSpecified
from .forms.forms import MongoModelForm
from .forms.form_utils import has_digit, make_key
from .utils import translate_value, trim_field_key
from .views import AppListView, IndexView

logger = logging.getLogger(__name__)


class AppStore(object):

    def __init__(self, module):
        self.models = []
        for key in module.__dict__.keys():
            model_candidate = getattr(module, key)
            if hasattr(model_candidate, 'mongoadmin'):
                self.add_model(model_candidate)

    def add_model(self, model):
        model.name = model.__name__
        self.models.append(model)


class MongonautViewMixin(object):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """user-login, permission check."""
        self.set_mongoadmin()
        permission_name = self.get_permission()
        if not self.check_permission(permission_name):
            return HttpResponseForbidden("""you have no %s permission,
                                        please contact adminstrator."""\
                                         % ({'has_add_permission': u'add',
                                             'has_delete_permission': u'delete',
                                             'has_edit_permission': u'edit',
                                             'has_view_permission': u'view'
                                             }.get(permission_name)))
        return super(MongonautViewMixin, self).dispatch(*args, **kwargs)

    def check_permission(self, permission_name):
        """set permission for user."""
        self.set_permissions_in_context()
        return self.permission_context[permission_name]

    def get_permission(self):
        """get permission name for request."""
        return self.permission

    def render_to_response(self, context, **response_kwargs):
        # if it is IndexView or AppListView
        if isinstance(self, AppListView) or isinstance(self, IndexView):
            object_list = context.get('object_list', [])
            if not self.request.user.is_superuser:
                # 清除用户没有权限的应用
                app_names = [appstore.get('app_name', '') for appstore in object_list]
                to_be_remove = []
                for app_name in app_names:
                    if not self.request.user.has_module_perms(app_name):
                        to_be_remove.append(app_name)

                if to_be_remove:
                    if app_names == to_be_remove:
                        # if user has no perms.
                        return HttpResponseForbidden(u"抱歉,你没有权限浏览此内容,请联系管理员.")

                    object_list = [appstore for appstore in object_list\
                                   if appstore.get('app_name', '') not in to_be_remove]

                # 清除用户没有权限的集合
                user_all_perms = self.request.user.get_all_permissions()
                all_perms_set = set()
                for perms in user_all_perms:
                    all_perms_set.add(perms.split('_')[-1])
                for appstore in object_list:
                    appstore['obj'].models = [model for model in appstore['obj'].models \
                                           if model.mongoadmin.sql_object.lower() in all_perms_set]
            else:
                # 超级管理员不作处理
                pass

            navigation_list = []
            for appstore in object_list:
                if appstore['obj'].models:
                    # 制作导航栏
                    navigation_models = []
                    for model in appstore['obj'].models:
                        doc = model.__doc__
                        plural_name = doc.split('\n')[0] if doc else model.name
                        show_model = {
                            'name': model.name,
                            'plural': plural_name,
                        }
                        # 导航栏只需model名
                        navigation_models.append(show_model)
                    navigation_models.sort(key=lambda model: model['plural'])
                    app_name = appstore.get('app_name', '')
                    navigation_app = {
                        'app_name': app_name,
                        'app_plural': settings.MONGONAUT_APP_TABLE.get(app_name, app_name),
                        'models': navigation_models
                    }
                    navigation_list.append(navigation_app)
            # 导航栏放session中
            navigation_list.sort(key=lambda app: app['app_plural'])
            self.request.session['navigation_list'] = navigation_list

        return self.response_class(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            **response_kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(MongonautViewMixin, self).get_context_data(**kwargs)
        context['METISMENU_CSS'] = settings.MONGONAUT_METISMENU_CSS
        context['BOOSTRAP_SELECT_CSS'] = settings.MONGONAUT_BOOSTRAP_SELECT_CSS
        context['FONT_AWESOME'] = settings.MONGONAUT_FONT_AWESOME
        context['JQUERY_JS'] = settings.MONGONAUT_JQUERY_JS
        context['METISMENU_JS'] = settings.MONGONAUT_METISMENU_JS
        context['BOOSTRAP_CORE_JS'] = settings.MONGONAUT_BOOSTRAP_CORE_JS
        return context

    def get_mongoadmins(self):
        """ Returns a list of all mongoadmin implementations for the site """
        apps = []
        for app_name in settings.INSTALLED_APPS:
            mongoadmin = "{0}.mongoadmin".format(app_name)
            try:
                module = import_module(mongoadmin)
            except ImportError as e:
                if str(e).startswith("No module named"):
                    continue
                raise e

            app_store = AppStore(module)
            apps.append(dict(
                app_name=app_name,
                obj=app_store
            ))
        return apps

    def set_mongonaut_base(self):
        """ Sets a number of commonly used attributes """
        if hasattr(self, "app_label"):
            # prevents us from calling this multiple times
            return None
        self.app_label = self.kwargs.get('app_label')
        self.document_name = self.kwargs.get('document_name')

        # TODO Allow this to be assigned via url variable
        self.models_name = self.kwargs.get('models_name', 'models')

        # import the models file
        self.model_name = "{0}.{1}".format(self.app_label, self.models_name)
        try:
            self.models = import_module(self.model_name)
        except ImportError:
            raise http.Http404('No module name {0}.'.format(self.model_name))

    def set_mongoadmin(self):
        """ Returns the MongoAdmin object for an app_label/document_name style view
        """
        if hasattr(self, "mongoadmin"):
            return None

        if not hasattr(self, "document_name"):
            self.set_mongonaut_base()

        for mongoadmin in self.get_mongoadmins():
            for model in mongoadmin['obj'].models:
                # Match the first model.
                if model.name == self.document_name:
                    self.mongoadmin = model.mongoadmin
                    break
            else:
                continue
            break
        else:
            raise NoMongoAdminSpecified("No MongoAdmin for {0}.{1}".format(self.app_label, self.document_name))

    def set_permissions_in_context(self, context={}):
        """ Provides permissions for mongoadmin for use in the context"""
        if not hasattr(self, 'permission_context'):
            if not self.request.user.is_authenticated() or not self.request.user.is_active:
                self.permission_context = {
                    'has_edit_permission': False,
                    'has_add_permission': False,
                    'has_delete_permission': False,
                    'has_view_permission': False
                }
            else:
                edit_permission = self.mongoadmin.has_edit_permission(self.request, self.app_label)
                add_permission = self.mongoadmin.has_add_permission(self.request, self.app_label)
                delete_permission = self.mongoadmin.has_delete_permission(self.request, self.app_label)
                self.permission_context = {
                    'has_edit_permission': edit_permission,
                    'has_add_permission': add_permission,
                    'has_delete_permission': delete_permission
                }
                can_view = edit_permission or add_permission or delete_permission
                if not can_view:
                    can_view = self.mongoadmin.has_view_permission(self.request, self.app_label)
                self.permission_context['has_view_permission'] = can_view

        context.update(self.permission_context)
        return context


class MongonautFormViewMixin(object):
    """
    View used to help with processing of posted forms.
    Must define self.document_type for process_post_form to work.
    """

    def process_post_form(self, success_message=None, is_save=True):
        """
        As long as the form is set on the view this method will validate the form
        and save the submitted data.  Only call this if you are posting data.
        The given success_message will be used with the djanog messages framework
        if the posted data sucessfully submits.
        """

        # When on initial args are given we need to set the base document.
        if not hasattr(self, 'document') or self.document is None:
            self.document = self.document_type()
        self.form = MongoModelForm(model=self.document_type, instance=self.document,
                                   form_post_data=self.request.POST,
                                   files=self.request.FILES).get_form()
        self.form.is_bound = True
        if self.form.is_valid():

            self.document_map_dict = MongoModelForm(model=self.document_type).create_document_dictionary(self.document_type)
            self.new_document = self.document_type

            # Used to keep track of embedded documents in lists.  Keyed by the list and the number of the
            # document.
            self.embedded_list_docs = {}

            if self.new_document is None:
                messages.error(self.request, u"Failed to save document")
            else:
                self.new_document = self.new_document()
                for form_key in self.form.cleaned_data.keys():
                    if form_key == 'id' and hasattr(self, 'document'):
                        self.new_document.id = self.document.id
                        continue
                    self.process_document(self.new_document, form_key, None)

                if self.form.errors:
                    messages.error(self.request, u"数据有误,请检查!")
                    return self.form

                try:
                    if is_save:
                        self.new_document.save(force_insert=True)
                    else:
                        self.new_document.save()
                except NotUniqueError:
                    self.form.errors['id'] = u" "
                    error_message = u"重复插入数据,保存失败!"
                    success_message = ""
                except Exception as ex:
                    self.form.errors['id'] = u" "
                    error_message = u"插入数据错误,请联系管理员."
                    success_message = ""
                    logger.error("save document:{document} failed cause: {reason}"\
                                 .format(document=str(self.new_document._data),
                                         reason=ex))
                if success_message:
                    messages.success(self.request, success_message)
                else:
                    messages.error(self.request, error_message)

        return self.form

    def process_document(self, document, form_key, passed_key):
        """
        Given the form_key will evaluate the document and set values correctly for
        the document given.
        """
        if passed_key is not None:
            current_key, remaining_key_array = trim_field_key(document, passed_key)
        else:
            current_key, remaining_key_array = trim_field_key(document, form_key)

        key_array_digit = remaining_key_array[-1] if remaining_key_array and \
                                    has_digit(remaining_key_array) else None
        remaining_key = make_key(remaining_key_array)

        if current_key.lower() == 'id':
            raise KeyError(u"Mongonaut does not work with models which have"
                           "fields beginning with id_")

        # Create boolean checks to make processing document easier
        is_embedded_doc = (isinstance(document._fields.get(current_key, None),
                                      EmbeddedDocumentField)
                          if hasattr(document, '_fields') else False)
        is_list = not key_array_digit is None
        is_file = (isinstance(self.form.fields.get(current_key, None), FileField)
                   if hasattr(self.form, 'fields') else False)

        key_in_fields = current_key in document._fields.keys() \
                        if hasattr(document, '_fields') else False

        # This ensures you only go through each documents keys once,
        # and do not duplicate data
        if key_in_fields:
            if is_embedded_doc:
                self.set_embedded_doc(document, form_key, current_key, remaining_key)
            elif is_list:
                self.set_list_field(document, form_key, current_key, remaining_key, key_array_digit)
            elif is_file:
                # 自定义文件保存.
                save_func = getattr(document._fields[current_key], 'save_to_mongo', None)
                if callable(save_func):
                    save_func(document, self.form, current_key, form_key)
                else:
                    raise KeyError(u"You should define your own file process"
                                   "function in mongo filed call save_to_mongo")
            else:
                value = translate_value(document._fields[current_key],
                                        self.form.cleaned_data[form_key])
                # 自定义数据转换
                validate_method = getattr(document, 'validate_{key}'.format(key=current_key), None)
                if callable(validate_method):
                    try:
                        value = validate_method(value)
                    except ValidationError, ex:
                        self.form._errors[form_key] = self.form.error_class(ex.messages)

                setattr(document, current_key, value)

    def set_embedded_doc(self, document, form_key, current_key, remaining_key):

        # Get the existing embedded document if it exists, else created it.
        embedded_doc = getattr(document, current_key, False)
        if not embedded_doc:
            embedded_doc = document._fields[current_key].document_type_obj()

        new_key, new_remaining_key_array = trim_field_key(embedded_doc, remaining_key)
        self.process_document(embedded_doc, form_key, make_key(new_key, new_remaining_key_array))
        setattr(document, current_key, embedded_doc)

    def set_list_field(self, document, form_key, current_key, remaining_key, key_array_digit):

        document_field = document._fields.get(current_key)

        # Figure out what value the list ought to have
        # None value for ListFields make mongoengine very un-happy
        list_value = translate_value(document_field.field, self.form.cleaned_data[form_key])
        if list_value is None or (not list_value and not bool(list_value)):
            return None

        current_list = getattr(document, current_key, None)

        if isinstance(document_field.field, EmbeddedDocumentField):
            embedded_list_key = u"{0}_{1}".format(current_key, key_array_digit)

            # Get the embedded document if it exists, else create it.
            embedded_list_document = self.embedded_list_docs.get(embedded_list_key, None)
            if embedded_list_document is None:
                embedded_list_document = document_field.field.document_type_obj()

            new_key, new_remaining_key_array = trim_field_key(embedded_list_document, remaining_key)
            self.process_document(embedded_list_document, form_key, new_key)

            list_value = embedded_list_document
            self.embedded_list_docs[embedded_list_key] = embedded_list_document

            if isinstance(current_list, list):
                # Do not add the same document twice
                if embedded_list_document not in current_list:
                    current_list.append(embedded_list_document)
            else:
                setattr(document, current_key, [embedded_list_document])

        elif isinstance(current_list, list):
            current_list.append(list_value)
        else:
            setattr(document, current_key, [list_value])

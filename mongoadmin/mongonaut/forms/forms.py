# -*- coding: utf-8 -*-

from django import forms
from mongoengine.base import TopLevelDocumentMetaclass
from mongoengine.fields import EmbeddedDocumentField, ListField
from mongoengine import Document

from .form_mixins import MongoModelFormBaseMixin
from .form_utils import has_digit
from .form_utils import make_key
from .widgets import get_widget
from django.contrib.admin.templatetags.admin_static import static
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe


class MongoModelForm(MongoModelFormBaseMixin, forms.Form):
    """
    This class will take a model and generate a form for the model.
    Recommended use for this project only.

    Example:

    my_form = MongoModelForm(request.POST, model=self.document_type, instance=self.document).get_form()

    if self.form.is_valid():
        # Do your processing
    """

    def __init__(self, form_post_data=None, *args, **kwargs):
        """
        Overriding init so we can set the post vars like a normal form and generate
        the form the same way Django does.
        """
        kwargs.update({'form_post_data': form_post_data})
        super(MongoModelForm, self).__init__(*args, **kwargs)

    def set_fields(self):

        # Get dictionary map of current model
        # 由mongo_filed获取widget.
        if self.is_initialized:
            self.model_map_dict = self.create_document_dictionary(self.model_instance)
        else:
            self.model_map_dict = self.create_document_dictionary(self.model)

        form_field_dict = self.get_form_field_dict(self.model_map_dict)

        self.set_validate_js(form_field_dict)

        # Get base key for embedded field class, used in self.set_form_fields
        self.valid_base_keys = [model_key for model_key in self.model_map_dict.keys()
                                if not model_key.startswith("_")]
        self.set_form_fields(form_field_dict)

    def set_post_data(self):
        # Need to set form data so that validation on all post data occurs and
        # places newly entered form data on the form object.
        self.form.data = self.post_data_dict

        form_fields = self.form.fields.copy()
        # Specifically adding list field keys to the form so they are included
        # in form.cleaned_data after the call to is_valid
        for field_key, field in form_fields.iteritems():
            if has_digit(field_key):
                # We have a list field.
                base_key = make_key(field_key, exclude_last_string=True)

                # Add new key value with field to form fields so validation
                # will work correctly
                if isinstance(field, forms.SplitDateTimeField):
                    # rstrip `_0` and `_1`
                    self.update_fields(-2, field, base_key)
                else:
                    self.update_fields(None, field, base_key)

    def update_fields(self, index, field, base_key):
        for key in self.post_data_dict.keys():
            if base_key in key:
                self.form.fields.update({key[:index]: field})

    def get_form(self):
        self.set_fields()
        if self.post_data_dict is not None:
            self.set_post_data()
        return self.form

    def create_doc_dict(self, document, doc_key=None, owner_document=None):
        """
        Generate a dictionary representation of the document.  (no recursion)

        DO NOT CALL DIRECTLY
        """
        # Get doc field for top level documents
        if owner_document:
            doc_field = owner_document._fields.get(doc_key, None) if doc_key else None
        else:
            doc_field = document._fields.get(doc_key, None) if doc_key else None

        # Generate the base fields for the document
        doc_dict = SortedDict({"_document": document if owner_document is None else owner_document,
                    "_key": document.__class__.__name__.lower() if doc_key is None else doc_key,
                    "_document_field": doc_field})

        if not isinstance(document, TopLevelDocumentMetaclass) and doc_key:
            doc_dict.update({"_field_type": EmbeddedDocumentField})

        if isinstance(document, TopLevelDocumentMetaclass):
            # Note: 只有集合才能有此属性, 其余的如EmbeddedDocument没有这些属性.
            # 不在Add,Edit中显示,默认情况下在List下显示.
            only_show_in_list = getattr(document, 'only_show_in_list', ())
            # 在Edit界面只读, 在Add界面不显示.
            # TODO: getattr from document, not from mongoadmin.
            # so can remove if isinstance(document, TopLevelDocumentMetaclass)
            show_in_edit = getattr(document.mongoadmin, 'show_in_edit', ())
            # 与only_show_in_list相对的概念, 允许在Add, Edit界面中被编辑.
            allowed_edit = getattr(document, 'allowed_edit', document._fields_ordered)
            # 一定要有id, 否则无法修改数据.
            if 'id' not in allowed_edit:
                allowed_edit = ('id', ) + allowed_edit

            # 完全不在List,Add,Edit中显示, 在model中用作另外的用途.
            fake_list = getattr(document, 'fake_list', ())
        else:
            only_show_in_list, fake_list, show_in_edit = (), (), ()
            allowed_edit = document._fields_ordered

        for key in allowed_edit:
            if key in only_show_in_list or key in show_in_edit:
                continue
            if key in fake_list:
                continue
            field = document._fields.get(key)
            doc_dict[key] = field

        # doc_dict被显示在编辑界面(AddForm与EditForm)中.
        return doc_dict

    def create_list_dict(self, document, list_field, doc_key):
        """
        Genereates a dictionary representation of the list field. Document
        should be the document the list_field comes from.

        DO NOT CALL DIRECTLY
        """
        list_dict = {"_document": document}

        if isinstance(list_field.field, EmbeddedDocumentField):
            list_dict.update(self.create_document_dictionary(document=list_field.field.document_type_obj,
                                                             owner_document=document))

        # Set the list_dict after it may have been updated
        list_dict.update({"_document_field": list_field.field,
                          "_key": doc_key,
                          "_field_type": ListField,
                          "_widget": get_widget(list_field.field),
                          "_value": getattr(document, doc_key, None)})

        return list_dict

    def create_document_dictionary(self, document, document_key=None, owner_document=None):
        """
        Given document generates a dictionary representation of the document.
        Includes the widget for each for each field in the document.
        """
        doc_dict = self.create_doc_dict(document, document_key, owner_document)

        for doc_key, doc_field in doc_dict.iteritems():
            # Base fields should not be evaluated
            if doc_key.startswith("_"):
                continue

            if isinstance(doc_field, ListField):
                doc_dict[doc_key] = self.create_list_dict(document, doc_field, doc_key)

            elif isinstance(doc_field, EmbeddedDocumentField):
                doc_dict[doc_key] = self.create_document_dictionary(doc_dict[doc_key].document_type_obj,
                                                                    doc_key)
            else:
                doc_dict[doc_key] = {"_document": document,
                                     "_key": doc_key,
                                     "_document_field": doc_field,
                                     "_widget": get_widget(doc_dict[doc_key],
                                                           getattr(doc_field, 'disabled', False))}

        return doc_dict

    def set_validate_js(self, form_field_dict):
        js_option = JsOption()
        media = forms.Media()
        has_js = False
        for form_key, field_value in form_field_dict.iteritems():
            if not hasattr(field_value, 'document_field'):
                continue
            validate_js = getattr(field_value.document_field, 'validate_js', None)
            if not validate_js:
                continue
            for element in validate_js:
                if len(element) == 3 and element[-1].endswith('.js'):
                    media += forms.Media(js=[static("js/validate/{0}".format(element[-1]))])
                    has_js = True
            js_option[form_key] = validate_js
        self.form.validations = js_option
        if has_js:
            self.form.validation_media = media


class JsOption(object):
    """Config of Jquery validation.
    Example:
        $("#field_form").validate({
            onsubmit:true,// 是否在提交是验证
            onkeyup: false,
            onclick: false,
            errorClass: "validate-error",
            rules:{
                uid:{
                    required: true,
                    ccidCheck: true,
                    min: 0,
                },
                balance:{
                    required: true,
                    min: 0,
                }
            }
        })
    """

    def __init__(self):
        self.media_attrs = {}

    def __str__(self):
        render_text = ""
        for k, v in self.media_attrs.items():
            v = " ".join("{0}: {1}, ".format(ele[0], ele[1]) for ele in v)
            render_text += "%s: { %s },\n" % (k, v)
        return mark_safe(render_text)

    def __setitem__(self, name, value):
        if value:
            self.media_attrs[name] = value

    def __getitem__(self, name):
        return self.media_attrs.get(name, '')

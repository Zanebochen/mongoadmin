# -*- coding: utf-8 -*-
from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from mongoengine.fields import (URLField, ListField, ReferenceField,
                                DateTimeField, ObjectIdField, EmbeddedDocumentField)
from mongonaut.conf import settings
from mongonaut.fields import AdminImageURLField
from mongonaut.forms.widgets import absolute_media_path

register = template.Library()


def process_image_url(value, field):
    """AdminImageURLField, show picture or not"""
    if field.width:
        if not value:
            return u"无"
        return mark_safe("""
            <a href="{0}" target="_blank"><img src="{0}" width="{1}" a>
            """.format(absolute_media_path(value), field.width))
    # only show url address.
    elif value:
        shorten_value = ''
        if len(value) > 20:
            shorten_value = value[0:12] + "..."
        return mark_safe("""
            <a href="{0}" target="_blank" title="{0}" >{1}</a>
            """.format(absolute_media_path(value), shorten_value if shorten_value else value))
    else:
        return ""


def process_url(value, field):
    """URLField"""
    if value is None:
        return ""
    if len(value) > 20:
        shorten_value = value[0:12] + "..."
        return mark_safe("""
            <a href="{0}" target="_blank" title="{0}" >{1}</a>
            """.format(value, shorten_value))
    else:
        return mark_safe("""<a href="{0}">{1}</a>""".format(value, value))


def process_document(value, field):
    """Reference Document."""
    if value:
        app_label = value.__module__.rstrip(".models")
        document_name = value._class_name
        url = reverse("document_detail", kwargs={'app_label': app_label,
                                                 'document_name': document_name,
                                                 'id': value.id})
        return mark_safe("""<a href="{0}">{1}</a>""".format(url, value.__unicode__()))
    else:
        return ""


def process_time(value, field):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def process_list(value, field):
    base_list = value[:settings.MONGONAUT_LIST_MAX_SHOW]
    if isinstance(field.field, EmbeddedDocumentField):
        base_list = map(str, base_list)
    else:
        func = FIELD_TO_VALUE.get(type(field.field), None)
        if callable(func):
            def trans(value, field=field.field):
                return func(value, field)
            base_list = map(trans, base_list)

    return "[ {0} ]".format(", ".join(base_list))


def process_none(value, field):
    return value

FIELD_TO_VALUE = {
    ObjectIdField: process_none,
    ReferenceField: process_document,
    DateTimeField: process_time,
    AdminImageURLField: process_image_url,
    URLField: process_url,
    ListField: process_list
}


@register.simple_tag()
def get_document_value(document, key):
    """Get document value shown on Website.
    Args:
        @param: document, Mongo Document
        @param: key, str
    Note:
        User mark_safe if return html.
    """
    value = getattr(document, key, '')

    # user-defined method
    transform_method = getattr(document, 'transform_{key}'.format(key=key), None)
    if callable(transform_method):
        return transform_method(value)

    # field process
    field = document._fields.get(key, None)
    process_method = FIELD_TO_VALUE.get(type(field), None)
    if callable(process_method):
        return process_method(value, field)

    # scale string
    if isinstance(value, basestring) and len(value) > 20:
        shorten_value = value[0:12] + "..."
        return mark_safe("""<p title="{0}">{1}</p>""".format(value.encode('utf-8'),
                                                             shorten_value.encode('utf-8')))

    return value


@register.simple_tag()
def get_document_key(document, key):
    '''
    Get the verbose name shown in Web-site.
    Note: for translating field name into Chinese.
    '''

    _field = document._fields.get(key, None)
    # verbose_name, valid for Fields in Document, Not in EmbeddedDocument
    verbose_name = getattr(_field, 'verbose_name', None)
    if verbose_name:
        return verbose_name

    # for handling EmbeddedDocument.
    transform_table = getattr(document, 'transform_table', {})
    value = transform_table.get(key, '')
    if value:
        return value

    if key == 'id':
        return u'序号'

    # Default in Mongonaut config.
    value = settings.MONGONAUT_FIELD_TABLE.get(key, key)
    return value

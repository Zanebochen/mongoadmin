# -*- coding: utf-8 -*-
import datetime

from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from bson.objectid import ObjectId
from mongoengine import Document
from mongoengine.fields import URLField
from mongonaut.conf import settings
from mongonaut.fields import AdminImageURLField
from mongonaut.forms.widgets import absolute_media_path

register = template.Library()


@register.simple_tag()
def get_document_value(document, key):
    """前端显示的取值.
    Args:
        @param: document, Mongo Document
        @param: key, str
    Return:
        :返回需要在前端显示的内容.若要返回html语句, 需用mark_safe处理.
    """
    value = getattr(document, key)

    # 优先自定义处理
    transform_method = getattr(document, 'transform_{key}'.format(key=key), None)
    if transform_method:
        value = transform_method(value)
        return value

    if value is None:
        value = ""

    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, ObjectId):
        return value

    field = document._fields.get(key, None)
    # 自定义图片显示
    if isinstance(field, AdminImageURLField):
        # 设定需显示的格式
        if field.width:
            # 不需要设置field.height, 根据width进行等比例缩放.
            if not value:
                return u"无"
            return mark_safe("""
                <a href="{0}" target="_blank"><img src="{0}" width="{1}" a>
                """.format(absolute_media_path(value), field.width))
        # 不显示图,只显示url
        elif value:
            shorten_value = ''
            if len(value) > 20:
                shorten_value = value[0:12] + "..."
            return mark_safe("""
                <a href="{0}" target="_blank" title="{0}" >{1}</a>
                """.format(absolute_media_path(value), shorten_value if shorten_value else value))

    # URL处理显示
    if isinstance(field, URLField):
        if len(value) > 20:
            shorten_value = value[0:12] + "..."
            return mark_safe("""
                <a href="{0}" target="_blank" title="{0}" >{1}</a>
                """.format(value, shorten_value))
        else:
            return mark_safe("""<a href="{0}">{1}</a>""".format(value, value))

    # 引用文档显示
    if isinstance(value, Document):
        app_label = value.__module__.replace(".models", "")
        document_name = value._class_name
        url = reverse("document_detail", kwargs={'app_label': app_label,
                                                 'document_name': document_name,
                                                 'id': value.id})
        return mark_safe("""<a href="{0}">{1}</a>""".format(url, value.__unicode__()))

#     默认进行缩放处理
    if isinstance(value, basestring) and len(value) > 20:
        shorten_value = value[0:12] + "..."
        return mark_safe("""<p title="{0}" >{1}</p>""".format(value.encode('utf-8'),
                                                               shorten_value.encode('utf-8')))
    return value


@register.simple_tag()
def get_document_key(document, key):
    '''获取显示在前端的key值, 主要用于将英文属性名转为所需展示的中文.
    '''

    # 优先显示属性的help_text, 推荐使用.
    help_text = getattr(document._fields.get(key, None), 'help_text', None)
    if help_text:
        return help_text

    # 文档Model中的transform_table, 不推荐使用.
    transform_table = getattr(document, 'transform_table', {})
    value = transform_table.get(key, '')
    if value:
        return value

    if key == 'id':
        return u'序号'

    # 默认配置
    value = settings.MONGONAUT_FIELD_TABLE.get(key, key)
    return value


@register.simple_tag()
def add_two_numbers(number1, number2):
    '''
    User-defined adding cause template do not support adding.
    '''
    return number1 + number2


@register.simple_tag()
def get_operation_url(app_label, document_name, obj, operation_text):
    generate_url_func = obj.mongoadmin.operations.get(operation_text, None)
    if generate_url_func:
        url = generate_url_func(app_label, document_name, obj)
    else:
        url = ""
    return url

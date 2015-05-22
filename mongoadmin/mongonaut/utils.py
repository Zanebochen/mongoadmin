# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import os
import re
import inspect

from django.conf import settings
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION, DELETION
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, Model
from django.utils import importlib
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.encoding import force_text

from mongoengine import Document
from mongoengine.base import ObjectIdField, ValidationError
from mongoengine.fields import ReferenceField, StringField
from mongoengine.django.shortcuts import get_document_or_404

from .templatetags.mongonaut_tags import get_document_key


# Used to validate object_ids.
# Called by is_valid_object_id
OBJECT_ID = ObjectIdField()

MYSQL_CACHE = {}
OPERATION = {
    ADDITION: u'添加',
    CHANGE: u'修改'
}
LOG_EDIT_PATTERN = re.compile("[a-zA-Z]+:change")


def get_first_line_doc(content):
    return content.split('\n')[0] if content else ''


def is_valid_object_id(value):
    try:
        OBJECT_ID.validate(value)
        return True
    except ValidationError:
        return False


def translate_value(document_field, form_value):
    """
    Given a document_field and a form_value this will translate the value
    to the correct result for mongo to use.
    """
    value = form_value
    if isinstance(document_field, ReferenceField):
        value = get_document_or_404(document_field.document_type.objects,
                                    id=form_value) if form_value else None
    return value


def trim_field_key(document, field_key):
    """
    Returns the smallest delimited version of field_key that
    is an attribute on document.

    return (key, left_over_array)
    """
    trimming = True
    left_over_key_values = []
    current_key = field_key
    while trimming and current_key:
        if hasattr(document, current_key):
            trimming = False
        else:
            key_array = current_key.split("_")
            left_over_key_values.append(key_array.pop())
            current_key = u"_".join(key_array)

    left_over_key_values.reverse()
    return current_key, left_over_key_values


def load_class(path):
    """
    Load class from path.
    """
    mod_name, klass_name = path.rsplit('.', 1)

    try:
        mod = importlib.import_module(mod_name)
    except AttributeError as e:
        raise ImproperlyConfigured('Error importing {0}: "{1}"'.format(mod_name, e))

    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "{0}" does not define a "{1}" class'.format(mod_name, klass_name))

    return klass


def get_sql_object(mongo_object, app_label):
    """Get the mapping sql object."""
    prefix = "{app_label}.models".format(app_label=app_label)
    path = "{prefix}.{sql_object}".format(prefix=prefix,
                                          sql_object=mongo_object.mongoadmin.sql_object)
    mysql_object = MYSQL_CACHE.get(path, None)
    if not mysql_object:
        mysql_object = load_class(path)
        MYSQL_CACHE[path] = mysql_object
    return mysql_object


def log_addition(request, mongo_object, app_label):
    """
    Log that an object has been successfully added.

    The default implementation creates an admin LogEntry object.
    """
    if request.user.is_authenticated():
        mysql_object = get_sql_object(mongo_object, app_label)
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(mysql_object).pk,
            object_id=mongo_object.id,
            object_repr=force_text(mongo_object),
            action_flag=ADDITION
        )


def log_change(request, mongo_object, app_label, message):
    """
    Log that an object has been successfully changed.

    The default implementation creates an admin LogEntry object.
    """
    if request.user.is_authenticated():
        mysql_object = get_sql_object(mongo_object, app_label)
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(mysql_object).pk,
            object_id=mongo_object.id,
            object_repr=force_text(mongo_object),
            action_flag=CHANGE,
            change_message=message
        )


def get_from_change_data(form):
    """Get change data from form.
    @param form, Django.Form or subclass.
    @return: dict: {field: change_data}
    TODO: if USE_TZ = True, then something happen like this:
    'change 2015-05-22 12:06:09 to 2015-05-22 20:08:42+08:00'
    beacuse MongoEngine save the UTC in MongoDB, but do not set tz
    when get time from MongoDB, so the initial has not tz.
    """
    datas = {}
    for change_field in form.changed_data:
        initial_data = form.fields[change_field].initial
        newest_data = form.cleaned_data.get(change_field, "")
        datas[change_field] = u"change {0} to {1}".format(initial_data, newest_data).encode('utf-8')
    return datas


def log_deletion(request, mongo_object, app_label):
    """
    Log that an object will be deleted. Note that this method is called
    before the deletion.

    The default implementation creates an admin LogEntry object.
    """
    if request.user.is_authenticated():
        mysql_object = get_sql_object(mongo_object, app_label)
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(mysql_object).pk,
            object_id=mongo_object.id,
            object_repr=force_text(mongo_object),
            action_flag=DELETION
        )


def currentframe():
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except:
        return sys.exc_info()[2].tb_frame.f_back

if hasattr(sys, '_getframe'):
    currentframe = lambda: sys._getframe(1)


def get_latest_log_by_object_id(app_label, mongo_object, object_id):
    mysql_object = get_sql_object(mongo_object, app_label)
    ct_id = ContentType.objects.get_for_model(mysql_object).pk
    log_info = LogEntry.objects.filter(Q(object_id__exact=object_id),
                                       Q(content_type_id__exact=ct_id))\
                                       .select_related('user').first()
    return log_info


def get_last_editor(cls, app_label=""):
    """获取集合的最后一个修改记录的修改时间,动作,修改人姓名,修改内容."""
    if not app_label:
        # 获得调用栈信息
        frame = currentframe()
        caller_frame = frame.f_back
        caller_path = caller_frame.f_code.co_filename
        # 获取app_name
        tail = caller_path[len(settings.SITE_ROOT) + 1:]
        app_label = tail[: tail.find(os.path.sep)]

    last_editor = get_latest_log_by_object_id(app_label, cls, cls.id)
    if last_editor:
        user = last_editor.user
        flag = last_editor.action_flag
        message = process_message(cls, last_editor.change_message)
        if len(message) > 200:
            message = message[:200] + "..."

        action_time = localtime(last_editor.action_time)
        message = u"时间:{0} {1} {2}".format(action_time.strftime("%Y-%m-%d %H:%M:%S"),
                                           OPERATION.get(flag, u'未知'),
                                           message).encode('utf-8')
        name = user.last_name + user.first_name
        return mark_safe("""<p title="{0}">{1}</p>"""
                         .format(message, unicode(name) if name else user.username)
                         )
    return ''


def process_message(document, message):
    """正则表达式替换, 将日志里面的field转换成显示格式."""

    def process_re(match_object):
        value = match_object.group()
        field = value.split(':')[0]
        if field in document._fields_ordered:
            return "{0}:".format(get_document_key(document, field))
        return value

    new_message = LOG_EDIT_PATTERN.sub(process_re, message)
    return new_message


def transform_sys_last_editor(self, value):
    return get_last_editor(self, self.APP_LABEL)


def auto_add_sys_last_editor(module_name, *args):
    """自动为类加上系统默认的最后编辑者显示.
    @param mondule_name, str: 调用此函数的模板名称.
    @param args, tuple: 若args为空, 则调用此方法的models文件内所有文档都被处理,否则只处理args内制定对象.
    """

    app_name = module_name.split('.')[0]
    clsmembers = inspect.getmembers(sys.modules[module_name], inspect.isclass)

    # 获取基类是Document的类.
    documents = [item[1] for item in clsmembers if
                Document in getattr(item[1], '__bases__', ()) and
                # 调用此函数应用内定义的类.
                app_name in getattr(item[1], '__module__', '')]

    for document in documents:
        if not args or (args and document.__name__ in args):
            document.APP_LABEL = app_name

            # 仅显示最后编辑人而不允许修改.
            only_show_in_list = getattr(document, 'only_show_in_list', None)
            if only_show_in_list:
                only_show_in_list += ('sys_last_editor', )
            else:
                only_show_in_list = ('sys_last_editor', )
            document.only_show_in_list = only_show_in_list

            # 添加到Document内置属性.
            document._fields_ordered += ('sys_last_editor', )
            sys_last_editor = StringField(verbose_name="最后编辑人")
            document._fields['sys_last_editor'] = sys_last_editor
            document.sys_last_editor = sys_last_editor
            # 添加转换函数.
            document.transform_sys_last_editor = transform_sys_last_editor


def auto_create_mysqlmodel_for_mongo(
    sql_model_class_name="Mysql{document_class}",
    sql_model_table_name="{app_name}_mongo_{document_class}",
    sql_model_verbose_name=None,
    auto_add_sql=1):
    """
    @params {string} sql_model_class_name: 为Django创建的model名
    @params {string} sql_model_table_name: mysql数据库表名的格式
    @params {string} sql_model_verbose_name: 默认用Document的class_doc
    @params {int} auto_add_sql:
        1, 自动将调用者的命名空间中所有Document的子类都各生成一张mysql的表
        0, 调用者的命名空间中所有Document的子类，且该子类含有add2mysql=1属性时,才生成一张mysql表

    TODO: When model has defined its own MysqlModel, then pass.
    """

    # 获得调用栈信息
    frame = currentframe()
    caller_frame = frame.f_back
    local = caller_frame.f_locals
    caller_path = caller_frame.f_code.co_filename
    # 获取app_name
    tail = caller_path[len(settings.SITE_ROOT) + 1:]
    app_name = tail[: tail.find(os.path.sep)]

    document = [item[1] for item in local.items() if
                Document in getattr(item[1], '__bases__', ()) and
                # 调用此函数应用内定义的类.
                app_name in getattr(item[1], '__module__', '')]

    if auto_add_sql == 0:
        document = [mongo for mongo in document if
                    getattr(mongo, 'auto_add_sql', 0) is 1]
    for mongo in document:
        cls_name = sql_model_class_name.format(document_class=mongo.__name__)
        verbose_name = sql_model_verbose_name or get_first_line_doc(mongo.__doc__) or mongo.__name__
        # dynamic create django mysql model
        t = type(cls_name,
                 (Model,),
                 {"Meta": type(
                     "Meta",
                     (),
                     {'db_table': sql_model_table_name.format(
                         app_name=app_name.lower(),
                         document_class=mongo.__name__.lower()),
                         'verbose_name': verbose_name,
                         'verbose_name_plural': verbose_name,
                      }),
                  '__doc__': mongo.__doc__,
                  '__module__': mongo.__module__
                  })
        local[cls_name] = t

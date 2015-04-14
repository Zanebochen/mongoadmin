# -*- coding: utf-8 -*-
"""
自定义Mongoengine的Field
New:
    widget: 前端显示的控件的类型
    form_field: 自定义Mongoengine Field 的 django form field, 用于校验数据.
    validate_js, 元组列表: 前端js的校验方法(详见JQuery validation.), 需要有序.
    attr_list, 列表: 前端属性列表,用于绑定js事件.
    help_text, str: 每个field的自带属性, 现被用作页面说明字段显示.

说明:
    1.为了兼容前端,并使得 ModelField的限制条件能够同时满足MongoEngine与Jquery Validation,不建议使用
    Mongoengine自身的Field域.若需使用,新建类继承原有类并加入validate_js属性与process_validate_js函数.
    2.process_validate_js函数.对照http://jqueryvalidation.org/documentation/中
    List of built-in Validation methods或自定义jQuery.validator.addMethod函数.
    3.validate_js元组: ([校验函数名称], [校验函数值], [存有校验函数的js文件名(包含.js后缀)])
"""
from __future__ import absolute_import
import logging
import os
import datetime

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import default_storage
from django.utils.encoding import force_str, force_text

from mongoengine import StringField, IntField, URLField, EmailField

from .forms.widgets import MongoImageWidget, MongoSelectWidget, IntChoiceField

logger = logging.getLogger(__name__)

__all__ = ['AdminStringField', 'AdminUnsignedIntField', 'AdminIntSelectField',
           'AdminURLField', 'AdminEmailField', 'AdminImageURLField']


class AdminStringField(StringField):
    def __init__(self, widget=None, form_field=forms.CharField, validate_js=[],
                 attr_list=[], **kwargs):
        self.widget = widget
        self.form_field = form_field
        super(AdminStringField, self).__init__(**kwargs)
        self.validate_js = []
        self.attr_list = attr_list
        self.process_validate_js(validate_js)

    def process_validate_js(self, validate_js):
        if self.required and not self.widget:  # 在上传图片空间中,编辑有图片的文档时,检测不到文件名.待解决.
            self.validate_js.append(('required', 'true'))
        if self.max_length is not None:
            self.validate_js.append(('maxlength', self.max_length))
        if self.min_length is not None:
            self.validate_js.append(('minlength', self.min_length))
        if isinstance(validate_js, list):
            self.validate_js += validate_js


class AdminUnsignedIntField(IntField):
    def __init__(self, widget=None, form_field=forms.IntegerField, validate_js=[], attr_list=[], **kwargs):
        self.widget = widget
        self.form_field = form_field
        super(AdminUnsignedIntField, self).__init__(**kwargs)
        self.validate_js = []
        self.attr_list = attr_list
        self.process_validate_js(validate_js)

    def process_validate_js(self, validate_js):
        self.validate_js.append(('digits', 'true'))
        if self.required:
            self.validate_js.append(('required', 'true'))
        if self.min_value is not None:
            self.validate_js.append(('min', self.min_value))
        if self.max_value is not None:
            self.validate_js.append(('max', self.max_value))
        if isinstance(validate_js, list):
            self.validate_js += validate_js


class AdminIntField(AdminUnsignedIntField):
    """AdminUnsignedIntField仅支持正整数输入，AdminIntField支持所有整数（正，负， 零）"""
    def process_validate_js(self, validate_js):
        if self.required:
            self.validate_js.append(('required', 'true'))
        if self.min_value is not None:
            self.validate_js.append(('min', self.min_value))
        if self.max_value is not None:
            self.validate_js.append(('max', self.max_value))
        # 添加自定义插件
        self.validate_js += [('integerCheck', 'true', 'integerCheck.js')]

        if isinstance(validate_js, list):
            self.validate_js += validate_js


class AdminIntSelectField(AdminUnsignedIntField):
    """
    choices = ((1, 'a'), (2, 'b'))
    """
    def __init__(self, choices=(), widget=MongoSelectWidget,
                 form_field=IntChoiceField, **kwargs):
        if not isinstance(choices, tuple) or not choices:
            raise ValueError('choices needs to be type tuple and valued.')
        super(AdminIntSelectField, self).__init__(choices=choices,
                                                  form_field=form_field,
                                                  widget=widget,
                                                  **kwargs)

    def to_python(self, value):
        try:
            value = int(value)
            for k, v in self.choices:
                if k == value:
                    return v
        except ValueError:
            pass
        return value

    def to_mongo(self, value):
        """Convert a Python type to a MongoDB-compatible type.
        """
        value = self.value_to_key(value)
        return value

    def _validate(self, value, **kwargs):
        """not check choices."""
        # check validation argument
        if self.validation is not None:
            if callable(self.validation):
                if not self.validation(value):
                    self.error('Value does not match custom validation method')
            else:
                raise ValueError('validation argument for "%s" must be a '
                                 'callable.' % self.name)

        self.validate(value, **kwargs)

    def validate(self, value):
        try:
            value = self.value_to_key(value)
            value = int(value)
        except:
            self.error('%s could not be converted to int' % value)

        if self.min_value is not None and value < self.min_value:
            self.error('Integer value is too small')

        if self.max_value is not None and value > self.max_value:
            self.error('Integer value is too large')

    def prepare_query_value(self, op, value):
        if value is None:
            return value
        value = self.value_to_key(value)
        return int(value)

    def value_to_key(self, value):
        for k, v in self.choices:
            if v == value:
                return k
        else:
            return value


class AdminURLField(URLField):
    def __init__(self, widget=None, form_field=forms.URLField, validate_js=[], attr_list=[], **kwargs):
        self.widget = widget
        self.form_field = form_field
        super(AdminURLField, self).__init__(**kwargs)
        self.validate_js = []
        self.attr_list = attr_list
        self.process_validate_js(validate_js)

    def process_validate_js(self, validate_js):
        self.validate_js.append(('url', 'true'))
        if self.required:
            self.validate_js.append(('required', 'true'))
        if self.max_length is not None:
            self.validate_js.append(('maxlength', self.max_length))
        if self.min_length is not None:
            self.validate_js.append(('minlength', self.min_length))
        if isinstance(validate_js, list):
            self.validate_js += validate_js

    def validate(self, value):
        """如果不是必要并且值为空,则校验成功."""
        if not value and not self.required:
            return
        super(AdminURLField, self).validate(value)


class AdminEmailField(EmailField):
    def __init__(self, widget=None, form_field=forms.EmailField, validate_js=[],
                 attr_list=[], **kwargs):
        self.widget = widget
        self.form_field = form_field
        super(AdminEmailField, self).__init__(**kwargs)
        self.validate_js = []
        self.attr_list = attr_list
        self.process_validate_js(validate_js)

    def process_validate_js(self, validate_js):
        self.validate_js.append(('email', 'true'))
        if self.required:
            self.validate_js.append(('required', 'true'))
        if self.max_length is not None:
            self.validate_js.append(('maxlength', self.max_length))
        if self.min_length is not None:
            self.validate_js.append(('minlength', self.min_length))
        if isinstance(validate_js, list):
            self.validate_js += validate_js


class AdminImageURLField(AdminStringField):
    """
    Acutally, this filed save the return url and
    the file object is saved by elsewhere.
    """
    def __init__(self, width=120, height=100, max_length=255,
                 widget=MongoImageWidget,
                 form_field=forms.ImageField,
                 validate_js=[('extension', '''"png|jpe?g|gif"'''),
                              ('filesizeCheck', 2097152, 'fileCheck.js')],
                 upload_to="",
                 storage=None,
                 **kwargs):
        self.width = width
        # height not used, just use width.
        # equal proportion according to width.
        self.height = height
        self.widget = widget
        self.upload_to = upload_to
        self.storage = storage or default_storage
        super(AdminImageURLField, self).__init__(max_length=max_length,
                                                 widget=widget,
                                                 form_field=form_field,
                                                 validate_js=validate_js, **kwargs)

    def get_directory_name(self):
        return os.path.normpath(force_text(datetime.datetime.now().strftime(force_str(self.upload_to))))

    def get_filename(self, filename):
        return os.path.normpath(self.storage.get_valid_name(os.path.basename(filename)))

    def generate_filename(self, filename):
        return os.path.join(self.get_directory_name(), self.get_filename(filename))

    def save_to_mongo(self, document, form, current_key, form_key):
        """处理文件下载,仅保存上传成功后的url."""
        content = form.cleaned_data.get(form_key, None)
        error_message = ""
        if isinstance(content, basestring):
            # 用户编辑时,向后台传入原先文件的url.
            setattr(document, current_key, content)
        elif isinstance(content, UploadedFile):
            try:
                file_name = self.generate_filename(content.name)
                value = self.storage.save(file_name, content)
                setattr(document, current_key, value)
            except:
                logger.error("save file error", exc_info=True)
            else:
                logger.debug('save file succeed, here to save file.')

        # 需校验文件是否允许为空, 前端js检测文件名是否存在的判断存在问题, 故后台判断.
        elif content is False:
            # 表示清除文件.
            if self.required:
                error_message = u"文件不能为空."
            else:
                setattr(document, current_key, "")
        elif content is None:
            # 处理前端传回来的空值.
            if self.required:
                error_message = u"文件不能为空."
        else:
            error_message = u"上传文件失败."
            logger.error("upload file failed cause wrong type object")

        if error_message:
            form._errors[form_key] = form.error_class(error_message)

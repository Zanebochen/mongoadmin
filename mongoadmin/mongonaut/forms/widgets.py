# -*- coding: utf-8 -*-

""" Widgets for mongonaut forms"""
import datetime
from pytz import utc

from django import forms
from django.contrib.admin.templatetags.admin_static import static
from django.utils.html import conditional_escape, format_html
from django.utils.encoding import force_text, smart_text
from django.utils.safestring import mark_safe
from django.forms.util import to_current_timezone, flatatt
from django.utils.six.moves.urllib.parse import urljoin
from django.utils.translation import ugettext as _
import dateutil.parser

from mongoengine.base import ObjectIdField
from mongoengine.fields import (BooleanField, DateTimeField, EmbeddedDocumentField,
                                ListField, ReferenceField, FloatField, EmailField,
                                DecimalField, URLField, IntField, StringField)

from mongonaut.conf import settings


def absolute_media_path(path, prefix=None):
    if path.startswith(('http://', 'https://', '/')):
        return path
    if prefix is None:
        prefix = settings.MEDIA_URL
    return urljoin(prefix, path)


class MongoFileInput(forms.ClearableFileInput):

    template_with_initial = '%(initial_text)s %(initial)s %(clear_template)s<br/>%(input_text)s %(input)s'

    def input_render(self, name, value, attrs=None):
        """
        Super Class Input render method.
        """
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return format_html('<input{0} />', flatatt(final_attrs))

    def render(self, name, value, attrs=None):
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'clear_template': '',
            'clear_checkbox_label': self.clear_checkbox_label,
        }
        template = '%(input)s'
        substitutions['input'] = self.input_render(name, value, attrs)

        if value:
            template = self.template_with_initial
            substitutions['initial'] = format_html(self.url_markup_template,
                                                   # url
                                                   absolute_media_path(value),
                                                   force_text(value))
            if not self.is_required:
                checkbox_name = self.clear_checkbox_name(name)
                checkbox_id = self.clear_checkbox_id(checkbox_name)
                substitutions['clear_checkbox_name'] = conditional_escape(checkbox_name)
                substitutions['clear_checkbox_id'] = conditional_escape(checkbox_id)
                substitutions['clear'] = forms.CheckboxInput().render(checkbox_name, False, attrs={'id': checkbox_id})
                substitutions['clear_template'] = self.template_with_clear % substitutions

        return mark_safe(template % substitutions)


class MongoFileWidget(MongoFileInput):
    template_with_initial = ('<p class="file-upload">%s</p>'
                            % MongoFileInput.template_with_initial)
    template_with_clear = ('<span class="clearable-file-input">%s</span>'
                           % MongoFileInput.template_with_clear)


class MongoImageWidget(MongoFileInput):
    template_with_initial = ('<p class="file-upload">%s</p>'
                            % MongoFileInput.template_with_initial)
    template_with_clear = ('<span class="clearable-file-input">%s</span>'
                           % MongoFileInput.template_with_clear)

    url_markup_template = '''
    <a href="{0}" target="_blank"><img src="{0}" width="100"/></a>
    '''


class MongoSelectWidget(forms.Select):

    @property
    def media(self):
        """下拉框控件使用bootstrap-select的
        """
        return forms.Media(js=[settings.MONGONAUT_BOOSTRAP_SELECT_JS, ])

    def __init__(self, attrs=None, choices=()):
        final_attrs = {'class': 'selectpicker'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(MongoSelectWidget, self).__init__(attrs=final_attrs, choices=choices)


class MongoLocationWidget(forms.Select):
    """自定义位置控件"""
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        final_attrs['style'] = 'width:110px;'
        final_attrs['title'] = 'location_select'
        output = [format_html('<select{0}>', flatatt(final_attrs))]
        # 如果value存在,前端显示.
        if not choices and value:
            choices = ((value, value),)
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))


class MongoAreaCitySelectWidget(forms.MultiWidget):

    def __init__(self, attrs=None):
        widgets = [MongoLocationWidget, MongoLocationWidget, MongoLocationWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def decompress(self, value):
        try:
            province, city, area = value.split(' ')
            return [province, city, area]
        except:
            return ['', '', '']

    def value_from_datadict(self, data, files, name):
        return ' '.join([widget.value_from_datadict(data, files, name + '_%s' % i)\
                         for i, widget in enumerate(self.widgets)])

    @property
    def media(self):
        """省市区js三级联动
        """
        return forms.Media(js=[static('mongonaut/js/jsAddress.js'), ])


class MongoAdminDateWidget(forms.DateInput):

    @property
    def media(self):
        js = ["calendar.js", "DateTimeShortcuts.js"]
        return forms.Media(js=[static("mongonaut/js/admin/%s" % path) for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vDateField', 'size': '10'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(MongoAdminDateWidget, self).__init__(attrs=final_attrs, format=format)

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        attrs = dict(self.attrs, **kwargs)
        if extra_attrs:
            extra_attrs = extra_attrs.copy()
            extra_attrs.pop('class', None)
            attrs.update(extra_attrs)
        return attrs


class MongoAdminTimeWidget(forms.TimeInput):

    @property
    def media(self):
        js = ["calendar.js", "DateTimeShortcuts.js"]
        return forms.Media(js=[static("mongonaut/js/admin/%s" % path) for path in js])

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'vTimeField', 'size': '8'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(MongoAdminTimeWidget, self).__init__(attrs=final_attrs, format=format)

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        attrs = dict(self.attrs, **kwargs)
        if extra_attrs:
            extra_attrs = extra_attrs.copy()
            extra_attrs.pop('class', None)
            attrs.update(extra_attrs)
        return attrs


class MongoSplitDateTime(forms.MultiWidget):

    def __init__(self, attrs=None):
        widgets = [MongoAdminDateWidget, MongoAdminTimeWidget]
        super(MongoSplitDateTime, self).__init__(widgets, attrs)

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
        return mark_safe(self.format_output(id_, output))

    def format_output(self, id_, rendered_widgets):
        """Add id, name, class for ListField and EmbeddedField."""
        return format_html('<p class="datetime {4}" id="{5}" name="{6}">{0} {1}<br />{2} {3}</p>',
                           _('Date:'), rendered_widgets[0],
                           _('Time:'), rendered_widgets[1],
                           self.attrs['class'], id_, id_.lstrip('id_'))

    def decompress(self, value):
        '''由于我们的MongoDB中集合里时间以String格式存储, 若用到时间控件则选进行格式转换.
        '''
        if value:
            try:
                if isinstance(value, basestring):
                    try:
                        value = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        # 任意格式str转DateTime.
                        value = dateutil.parser.parse(value)
                # MongoDB中的DateTimeField转化成python格式时并没有带上timezone信息, 默认是UTC.
                value = to_current_timezone(utc.localize(value))
                return [value.date(), value.time().replace(microsecond=0)]
            except Exception:
                pass
        return [None, None]


def get_widget(model_field, disabled=False):

    widget = getattr(model_field, 'widget', None)
    if widget is not None:
        return widget()

    attrs = get_attrs(model_field, disabled)

    if isinstance(model_field, IntField):
        return forms.NumberInput(attrs=attrs)

    if isinstance(model_field, EmailField):
        return forms.EmailInput(attrs=attrs)

    elif hasattr(model_field, "max_length") and not model_field.max_length:
        attrs['rows'] = 3
        return forms.Textarea(attrs=attrs)

    elif isinstance(model_field, DateTimeField):
        return MongoSplitDateTime(attrs={'class': ''})

    elif isinstance(model_field, BooleanField):
        return forms.CheckboxInput(attrs=attrs)

    elif isinstance(model_field, ReferenceField):
        return forms.Select(attrs=attrs)

    elif model_field.choices:
        return MongoSelectWidget(attrs=attrs)

    elif isinstance(model_field, ListField) or isinstance(model_field,
                                                          EmbeddedDocumentField):
        return None

    else:
        return forms.TextInput(attrs=attrs)


def get_attrs(model_field, disabled=False):
    attrs = {'class': 'span6 xlarge'}

    # 加载field自定义属性
    event_list = getattr(model_field, "attr_list", [])
    for event in event_list:
        if len(event) == 2:
            attrs[event[0]] = event[1]

    if disabled or isinstance(model_field, ObjectIdField):
        attrs['class'] += ' disabled'
        attrs['readonly'] = 'readonly'
    return attrs

FIELD_MAPPING = {
    IntField: forms.IntegerField,
    StringField: forms.CharField,
    FloatField: forms.FloatField,
    BooleanField: forms.BooleanField,
    DateTimeField: forms.SplitDateTimeField,
    DecimalField: forms.DecimalField,
    URLField: forms.URLField,
    EmailField: forms.EmailField
}


def get_form_field_class(model_field):
    """
    Gets the default form field  for a mongoenigne field when show form.
    """
    form_field = getattr(model_field, 'form_field', None)
    return form_field if form_field \
        else FIELD_MAPPING.get(model_field.__class__, forms.CharField)

WIDGET_MAPPING = {
    forms.NumberInput: forms.IntegerField,
    forms.Textarea: forms.CharField,
    forms.TextInput: forms.CharField,
    forms.CheckboxInput: forms.BooleanField,
    forms.EmailInput: forms.EmailField,
    MongoSplitDateTime: forms.SplitDateTimeField,
    MongoAdminDateWidget: forms.DateField,
    MongoAdminTimeWidget: forms.TimeField,
    MongoImageWidget: forms.ImageField,
    MongoFileWidget: forms.FileField,
}


def get_form_field_class_from_widget(field, widget):
    """用户自定义的transform_widget, 亦需自定义Forms Field."""
    form_field = getattr(field, 'form_field', None)
    return form_field if form_field \
        else WIDGET_MAPPING.get(widget.__class__, forms.CharField)


# --------------------------Form Field--------------------------------
class IntChoiceField(forms.ChoiceField):
    """将前端返回的值改为int而非原来的unicode"""
    def to_python(self, value):
        "Returns a int object."
        if value in self.empty_values:
            return ''
        try:
            value = int(value)
            return value
        except:
            return smart_text(value)

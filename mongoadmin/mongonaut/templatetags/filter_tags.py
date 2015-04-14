#-*- coding:utf-8 -*-
from django import template
register = template.Library()

COVER_ATTRS = ['widget', 'help_text', 'choices']


@register.inclusion_tag('_fields.html', takes_context=True)
def get_search_fields(context, document=None, instance=None, template='_fields.html'):
    modelfilter = document.mongoadmin.filterobject(instance)
    form = modelfilter.form
    filters = modelfilter.filters
    fields = []

    for field in form:
        filter_field = filters.get(field.name)
        for attrname in COVER_ATTRS:
            if not hasattr(filter_field, attrname):
                continue

            attr = getattr(filter_field, attrname)
            if attr and hasattr(field, attrname):
                setattr(field, attrname, attr)
            elif attr and hasattr(field.field, attrname):
                setattr(field.field, attrname, attr)

        append_text = lookup_type_2_words.get(filter_field.lookup_type)
        if append_text:
            field.help_text += append_text

        fields.append(field)
    return {'fields': fields,
            'media': form.media,
            'template': template}

lookup_type_2_words = {
        "iexact": "不等于",
        "contains": '包涵',
        'icontains': "不包涵",
        'gt': "大于",
        'gte': "小于",
        'lt': "小于",
        'lte': "小于等于",
        'isnull': "为空",
}

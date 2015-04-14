# -*- coding: utf-8 -*-
from example.models import MiccardAnchor
from mongonaut.filters.filterset import FilterSet
from mongonaut.filters.filters import MultipleValueFilter, DateFilter
from mongonaut.forms.widgets import MongoAdminDateWidget


class MiccardAnchorFilter(FilterSet):
    uid = MultipleValueFilter()
    signtime = DateFilter(widget=MongoAdminDateWidget())

    class Meta:
        model = MiccardAnchor
        fields = ['uid', 'signtime']

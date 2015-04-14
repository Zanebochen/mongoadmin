# flake8: noqa
from __future__ import absolute_import
from .filterset import FilterSet
from .filters import *

from django import template
template.add_to_builtins('mongonaut.templatetags.filter_tags')

VERSION = (0, 7)


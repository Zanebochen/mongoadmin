from django import template
template.base.add_to_builtins('mongonaut.templatetags.mongonaut_tags')

__author__ = 'Zanebo Chen'

VERSION = (0, 0, 3)


def get_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])
    if VERSION[2]:
        version = '%s.%s' % (version, VERSION[2])
    return version

__version__ = get_version()
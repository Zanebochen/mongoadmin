"""Development settings and globals."""
from __future__ import absolute_import

from .base import *

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
########## END DEBUG CONFIGURATION

# When template fail, this will show more verbose error.
TEMPLATE_STRING_IF_INVALID = "INVALID EXPRESSION: %s"

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': normpath(join(SITE_ROOT, 'db.sqlite3')),
    }
}

# MongoDB Config
MONGODB_DATABASE = {
    "host": "127.0.0.1",
    "port": 27017,
    "db": "mongonaut",
}

########## END DATABASE CONFIGURATION


########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
########## END CACHE CONFIGURATION


########## TOOLBAR CONFIGURATION
# # See: http://django-debug-toolbar.readthedocs.org/en/latest/installation.html#explicit-setup
# INSTALLED_APPS += (
#     'debug_toolbar',
# )
# 
# MIDDLEWARE_CLASSES += (
#     'debug_toolbar.middleware.DebugToolbarMiddleware',
# )
# 
# DEBUG_TOOLBAR_PATCH_SETTINGS = False
# 
# # http://django-debug-toolbar.readthedocs.org/en/latest/installation.html
# INTERNAL_IPS = ('127.0.0.1',)
########## END TOOLBAR CONFIGURATION

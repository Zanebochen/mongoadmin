# -*- coding: utf-8 -*-
from django import http


class NoMongoAdminSpecified(http.Http404):
    """ Called when no MongoAdmin is specified. Unlike to ever be called."""
    pass

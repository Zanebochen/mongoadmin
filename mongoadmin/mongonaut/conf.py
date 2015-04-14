# -*- coding: utf-8 -*-
from django.conf import settings  # @UnusedImport, not obviously used but need.
from appconf import AppConf


class MongonautConf(AppConf):
    FIELD_TABLE = {}
    APP_TABLE = {}

    # CSS File CDN
    METISMENU_CSS = "http://cdn.bootcss.com/metisMenu/1.1.0/metisMenu.min.css"
    FONT_AWESOME = "http://cdn.bootcss.com/font-awesome/4.1.0/css/font-awesome.min.css"
    BOOSTRAP_SELECT_CSS = "http://cdn.bootcss.com/bootstrap-select/1.6.3/css/bootstrap-select.min.css"

    # JS File CDN
    JQUERY_JS = "http://cdn.bootcss.com/jquery/1.11.1/jquery.min.js"
    METISMENU_JS = "http://cdn.bootcss.com/metisMenu/1.1.0/metisMenu.min.js"
    BOOSTRAP_CORE_JS = "http://cdn.bootcss.com/bootstrap/3.3.0/js/bootstrap.min.js"
    BOOSTRAP_SELECT_JS = "http://cdn.bootcss.com/bootstrap-select/1.6.3/js/bootstrap-select.min.js"
    JQUERY_VALIDATE_JS = "http://ajax.aspnetcdn.com/ajax/jquery.validate/1.13.1/jquery.validate.min.js"
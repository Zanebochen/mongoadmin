# -*- coding: utf-8 -*-
"""
常见Document类属性说明:
    1.Class.__doc__: 集合对象的说明.第一行被显示在网页中.
    2.`transform_`开头函数是转换单一属性的显示,Mongo->Page.
    3.`validate_`开头的函数为校验,转换对应属性的值,Page->Mongo.
    4.only_show_in_list表示原Mongo数据库中不存在, 但在list表格中需要显示的属性.
    5.allowed_edit, 与only_show_in_list相对的概念, 允许在编辑界面中被编辑.
    6.fake_list, 完全不在List,Add,Edit中显示, 在model中用作另外的用途.

常用AdminField说明:
1.含有前缀Admin的Field继承自MongoEngine原有的Field, 只是增加了widget, form_fild,
validate_js, process_validate()等.
2.对应关系:
FieldName    Type    FormField    Widget    Note
---------    ----    ---------    ------    ----
AdminStringField    String    CharField    Textarea    如果有max_length属性, 则widget为TextInput
AdminUnsignedIntField    Int32    IntegerField    NumberInput    整数
AdminIntField    Int32    IntegerField    NumberInput    正整数
AdminIntSelectField    Int32    IntChoiceField    MongoSelectWidget
对下拉框选择控件的封装.如choices=((1, '男'), (2, '女')), DB里存1或2, 页面上显示'男'或'女'
AdminURLField    String    URLField    TextInput    URL地址
AdminEmailField    String    EmailField    TextInput    邮箱地址
AdminImageURLField    String    ImageField    MongoImageWidget
图片上传控件,默认调用Cotton存储,限制上传格式为png,gif,jpg, jpeg,大小为2M.width属性控制图片显示大小,无需设置height属性.

常见Field属性说明:
1.help_text: 属性的名称.
2.default: 默认值, 是一个值或者一个可调用对象.
3.widget: 前端显示的控件的类型
4.form_field: 自定义Mongoengine Field 的 django form field, 用于校验数据.
5.validate_js, 元组列表: 前端js的校验方法(详见JQuery validation.), 元组格式如下:
    ([校验函数名称], [校验函数值], [存有校验函数的js文件名(包含.js后缀)])
    JQuery Validation已有属性外, 目前已自定义的有:
    a.('ccidCheck', 'true', 'ccidCheck.js'), 校验ccid是否存在, 实际为ajax调用.
    b.('roomidCheck', 'true', 'roomidCheck.js'), 校验房间号是否存在.
    c.('isPhone', 'true', 'phoneCheck.js'), 校验手机号码.
    d.('isIdCardNo', 'true', 'isIdCardNo.js'), 校验身份证格式.
    e.('IpCheck', 'true', 'IpCheck.js'), 校验ip地址.
    增加校验的方法非常简单, 详情请参考以上任一函数或JQuery Validation官方文档.
6.MongoEngine各Field常用属性, 如: max_length, min_value等均支持.

"""
from django.db import models
from django.utils.safestring import mark_safe
from mongoengine import Document, DateTimeField
from mongonaut.fields import AdminStringField, AdminUnsignedIntField, \
    AdminIntSelectField, AdminIntField, AdminImageURLField
from mongonaut.forms.widgets import MongoAreaCitySelectWidget, \
    MongoAdminTimeWidget, MongoAdminDateWidget
from mongonaut.utils import get_last_editor
import datetime
import os

# 性别状态
GENDER_TYPE = ((0, '女'), (1, '男'), (2, '保密'))
# 获取models文件的app名字
APP_LABEL = __file__.split(os.path.sep)[-2]


class MiccardAnchor(Document):
    """娱乐主播库
    """
    uid = AdminIntField(min_value=0, help_text="主播CC号")
    signtime = DateTimeField(help_text="签约时间", default=datetime.datetime.now)
    nickname = AdminStringField(help_text="主播昵称", max_length=20)  # fake
    gender = AdminIntSelectField(choices=GENDER_TYPE, help_text="性别")
    cellphone = AdminUnsignedIntField(help_text="手机号码",
                                      validate_js=[('isPhone', 'true', 'phoneCheck.js')])
    poster = AdminImageURLField(help_text="海报", upload_to="测试_%y-%m-%d")

    admin_time = AdminStringField(help_text="时间(不包括日期)", widget=MongoAdminTimeWidget)
    admin_day = AdminStringField(help_text="日期(不包括时间)", widget=MongoAdminDateWidget)
    location = AdminStringField(help_text="所在地", widget=MongoAreaCitySelectWidget)
    # 日志记录
    last_editor = AdminStringField(help_text="最后编辑人")  # fake

    meta = {
        'indexes': ['uid', 'signtime'],
        'ordering': ['-signtime'],
        'collection': 'wonderful_miccard_anchor',
    }

    def __unicode__(self):
        return "MiccardAnchor_{0}".format(self.uid)

#     allowed_edit = ('id', 'uid', 'gender', 'cellphone', 'location')
    only_show_in_list = ('last_editor', 'nickname')

    transform_table = {
        'id': u'详情'
    }

    def transform_last_editor(self, value):
        return get_last_editor(self, APP_LABEL)

    def transform_nickname(self, value):
        if self.uid:
            return mark_safe("""<a href="#" target="_blank", title="{0}">{1}_nickname</a>"""\
                             .format(u'昵称'.encode('utf-8'), self.uid))
        else:
            return ""

    # text为操作名称, func为指定的函数名称.
    operations = [{
        'text': "修改时间",
        'func': 'change_time',
        }, {
        'text': "修改",
        'func': 'change',
        }, {
        'text': "跳转",
        'func': 'goto',
        }
    ]

    def goto(self):
        """跳转到新页面,注意一定要有schema前缀,如http://"""
        return "http://www.baidu.com"

    def change(self):
        """刷新页面"""
        return "refresh"

    def change_time(self):
        self.admin_time = datetime.datetime.now().strftime("%H:%M:%S")
        print self.admin_time
        self.save()


class MysqlMiccardAnchor(models.Model):
    class Meta:
        db_table = "example_miccard_anchor"
        verbose_name = u'娱乐主播库'
        verbose_name_plural = u'娱乐主播库'

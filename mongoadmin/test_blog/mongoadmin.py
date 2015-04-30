# -*- coding: utf-8 -*-
from __future__ import absolute_import
from mongonaut.sites import AutoPermissionMongoAdmin
from .models import User, Post


class PostAdmin(AutoPermissionMongoAdmin):
    pass


class UserAdmin(AutoPermissionMongoAdmin):
    pass

Post.mongoadmin = PostAdmin()
User.mongoadmin = UserAdmin()


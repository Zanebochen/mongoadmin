# -*- coding: utf-8 -*-
"""
The main purpose of these models is to do manual testing of
the mongonaut front end.  Do not use this code as an actual blog
backend.
"""

from mongoengine import (DateTimeField, BooleanField, Document,
                         EmbeddedDocument, EmbeddedDocumentField,
                         ListField, ReferenceField)
from mongonaut.fields import (AdminStringField, AdminEmailField,
                              AdminUnsignedIntField)

from datetime import datetime


class User(Document):
    """Test_User"""
    email = AdminEmailField(required=True, max_length=50)
    age = AdminUnsignedIntField()
    user_name = AdminStringField(max_length=50)

    def __unicode__(self):
        return self.user_name


class Comment(EmbeddedDocument):
    message = AdminStringField(default="DEFAULT EMBEDDED COMMENT", verbose_name="信息")
    author = ReferenceField(User)
    post_date = DateTimeField(verbose_name="发表时间")

    # ListField(EmbeddedDocumentField(ListField(Something)) is not currenlty supported.
    # UI, and lists with list inside them need to be fixed.  The extra numbers appened to
    # the end of the key and class need to happen correctly.
    # Files to fix: list_add.js, forms.py, and mixins.py need to be updated to work.
    # likes = ListField(ReferenceField(User))


class EmbeddedUser(EmbeddedDocument):
    email = AdminStringField(max_length=50, default="default-test@test.com")
    user_name = AdminStringField(max_length=50, verbose_name="用户名")
    created_date = DateTimeField()  # Used for testing
    is_admin = BooleanField()  # Used for testing
    # embedded_user_bio = EmbeddedDocumentField(Comment)
    # Not well supported. front-end is not good.
    friends_list = ListField(ReferenceField(User), verbose_name=u"联系人")

    # Not supportted see above comment on Comment
    # user_comments = ListField(EmbeddedDocumentField(Comment))


class Post(Document):
    # See Post.title.max_length to make validation better!
    title = AdminStringField(max_length=20, required=True,
                             unique=True, verbose_name="标题")
    content = AdminStringField(default="I am default content")
    author = ReferenceField(User)
    created_date = DateTimeField()
    published = BooleanField()
    creator = EmbeddedDocumentField(EmbeddedUser)
    published_dates = ListField(DateTimeField())
    tags = ListField(AdminStringField(max_length=30))
    past_authors = ListField(ReferenceField(User))
    comments = ListField(EmbeddedDocumentField(Comment))

    transform_table = {
        'message': u'信息',
        'post_date': u'发表时间'
    }

#     def save(self, *args, **kwargs):
#         if not self.created_date:
#             self.created_date = datetime.utcnow()
#             if not self.creator:
#                 self.creator = EmbeddedUser()
#                 self.creator.email = self.author.email
#                 self.creator.user_name = self.author.user_name
#         if self.published:
#             self.published_dates.append(datetime.utcnow())
#         super(Post, self).save(*args, **kwargs)


from mongonaut.utils import auto_create_mysqlmodel_for_mongo
auto_create_mysqlmodel_for_mongo()

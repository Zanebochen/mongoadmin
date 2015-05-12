from mongoengine import connect
from django.conf import settings

connect(**settings.MONGODB_DATABASE)

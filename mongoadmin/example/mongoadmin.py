from mongonaut.sites import PermissionMongoAdmin
from example.models import MiccardAnchor
from example.mongo_filter import MiccardAnchorFilter


class MiccardAnchorAdmin(PermissionMongoAdmin):
    sql_object = "MysqlMiccardAnchor"
    filterobject = MiccardAnchorFilter


MiccardAnchor.mongoadmin = MiccardAnchorAdmin()

# -*- coding: utf-8 -*-
try:
    import floppyforms as forms
except ImportError:
    from django import forms


class BaseMongoAdmin(object):

    search_fields = []

    filterobject = None

    # Show the fields to be displayed as columns
    # TODO: Confirm that this is what the Django admin uses
    list_fields = []

    # Exclude the fields to be displayed as columns.
    exclude_fields = []

    # shows uo on edit page while not on add page.
    show_in_edit = []

    ordering = None
    form = forms.ModelForm

    ############# inherit from django-admin but not achive #############
    # This shows up on the DocumentListView of the Posts.
    list_actions = []

    # This shows up in the DocumentDetailView of the Posts
    document_actions = []

    # shows up on a particular field
    field_actions = {}

    fields = None
    exclude = None
    fieldsets = None
    filter_vertical = ()
    filter_horizontal = ()
    radio_fields = {}
    prepopulated_fields = {}
    formfield_overrides = {}
    readonly_fields = ()

    list_display = ('__str__',)
    list_display_links = ()
    list_filter = ()
    list_select_related = False
    list_per_page = 100
    list_max_show_all = 200
    list_editable = ()
    save_as = False
    save_on_top = False
    ############# inherit from django-admin but not achive #############

    def has_view_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the mongonaut site.
        """
        return request.user.is_authenticated() and request.user.is_active

    def has_edit_permission(self, request):
        """ Can edit this object """
        return request.user.is_authenticated() and request.user.is_active and request.user.is_staff

    def has_add_permission(self, request):
        """ Can add this object """
        return request.user.is_authenticated() and request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request):
        """ Can delete this object """
        return request.user.is_authenticated() and request.user.is_active and request.user.is_superuser


def get_permission_codename(operation, object_name):
    return "%s_%s" % (operation, object_name.lower())


class PermissionMongoAdmin(BaseMongoAdmin):
    '''
    Add django admin permission into MongoAdmin
    '''

    # bound sql object name which offers permission control.
    sql_object = ''

    def __init__(self, *args, **kwargs):
        if not self.sql_object or not isinstance(self.sql_object, str):
            raise ValueError('you should define sql_object(a str object name) '
                             'used to permission control.')

        super(PermissionMongoAdmin, self).__init__(*args, **kwargs)

    def has_view_permission(self, request, app_label):
        codename = get_permission_codename("view", self.sql_object)
        return request.user.has_perm("%s.%s" % (app_label, codename))

    def has_edit_permission(self, request, app_label):
        codename = get_permission_codename("change", self.sql_object)
        return request.user.has_perm("%s.%s" % (app_label, codename))

    def has_add_permission(self, request, app_label):
        # Active superusers have all permissions.
        codename = get_permission_codename("add", self.sql_object)
        return request.user.has_perm("%s.%s" % (app_label, codename))

    def has_delete_permission(self, request, app_label):
        codename = get_permission_codename("delete", self.sql_object)
        return request.user.has_perm("%s.%s" % (app_label, codename))


class AutoPermissionMongoAdmin(PermissionMongoAdmin):
    """为mongoAdmin自动创建sql_object
    @param sql_object str: the mirror sql object name.如果
    mongo的admin的类名以"Admin"结尾,那么将自动创建属性sql_object="Mysql{不含Admin的类名}"
    """
    def __init__(self, mysqlmodel_class_name="Mysql{document_class}",
                 *args, **kwargs):
        cls_name = self.__class__.__name__
        if not getattr(self, 'sql_object', '') and cls_name.endswith('Admin'):
            document_class = cls_name[: cls_name.rfind('Admin')]
            self.sql_object = mysqlmodel_class_name.format(
                document_class=document_class)

        super(PermissionMongoAdmin, self).__init__(*args, **kwargs)

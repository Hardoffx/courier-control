from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CourierUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Courier Control', {'fields': ('role', 'phone')}),)
    list_display = ('username', 'first_name', 'last_name', 'role', 'is_active')

    def has_change_permission(self, request, obj=None):
        if obj and obj.archived_at:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Delete from Django admin is not part of the retention policy.
        return False

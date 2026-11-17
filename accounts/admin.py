from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CourierUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Courier Control', {'fields': ('role', 'phone')}),)
    list_display = ('username', 'first_name', 'last_name', 'role', 'is_active')

    def has_delete_permission(self, request, obj=None):
        # Delete from Django admin is not part of the retention policy.
        return False

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("Datos de REMSA", {"fields": ("job_title", "phone")}),)
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_staff")

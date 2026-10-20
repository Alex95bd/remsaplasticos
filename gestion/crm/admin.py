from django.contrib import admin

from .models import Party


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ["name", "rfc", "party_type", "contact_name", "is_active"]
    list_filter = ["party_type", "person_type", "is_active"]
    search_fields = ["name", "trade_name", "rfc", "email", "external_code"]
    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

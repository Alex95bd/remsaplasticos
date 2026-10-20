from django.contrib import admin

from .models import PriceChange, PriceList, PriceListItem


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "currency", "customer", "valid_from", "valid_until", "is_active"]
    inlines = [PriceListItemInline]


@admin.register(PriceChange)
class PriceChangeAdmin(admin.ModelAdmin):
    list_display = ["created_at", "price_list", "product", "old_price", "new_price", "source", "user"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

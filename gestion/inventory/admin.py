from django.contrib import admin

from .models import Location, Stock, StockMovement, Warehouse

admin.site.register(Warehouse)
admin.site.register(Location)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["product", "warehouse", "quantity", "min_quantity"]
    readonly_fields = ["quantity"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["created_at", "kind", "product", "warehouse", "quantity", "balance_after", "user"]
    list_filter = ["kind", "warehouse"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

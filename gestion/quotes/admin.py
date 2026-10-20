from django.contrib import admin

from .models import Quote, QuoteFollowUp, QuoteItem


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in QuoteItem._meta.fields if f.name != "id"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ["folio", "customer", "owner", "issue_date", "status", "total", "currency"]
    list_filter = ["status", "currency"]
    search_fields = ["folio", "customer__name"]
    readonly_fields = ["folio", "subtotal", "discount_total", "tax_total", "total", "created_at", "updated_at"]
    inlines = [QuoteItemInline]


admin.site.register(QuoteFollowUp)

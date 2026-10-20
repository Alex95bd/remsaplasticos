from django.contrib import admin

from .models import Category, Product, UnitOfMeasure


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "product_type", "unit", "is_active")
    list_filter = ("is_active", "product_type", "category")
    search_fields = ("sku", "name", "external_code")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

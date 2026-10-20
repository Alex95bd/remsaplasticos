from django.db import transaction
from rest_framework import serializers, viewsets

from audit.models import AuditLog
from audit.services import diff_snapshots, log_action, model_snapshot

from .models import Category, Product, UnitOfMeasure, normalize_sku
from .views import filter_products

PRICE_FIELDS = ("reference_price", "currency")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "is_active"]


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = ["id", "code", "name", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    unit_code = serializers.CharField(source="unit.code", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "description",
            "category",
            "category_name",
            "product_type",
            "unit",
            "unit_code",
            "presentation",
            "capacity_ml",
            "height_mm",
            "diameter_mm",
            "weight_g",
            "reference_price",
            "currency",
            "is_active",
            "external_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and not request.user.has_perm("catalog.view_reference_price"):
            for name in PRICE_FIELDS:
                self.fields.pop(name, None)

    def to_internal_value(self, data):
        if isinstance(data.get("sku"), str):
            data = data.copy()
            data["sku"] = normalize_sku(data["sku"])
        return super().to_internal_value(data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class UnitOfMeasureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer


class ProductViewSet(viewsets.ModelViewSet):
    """Productos. No se permite eliminar: los productos se desactivan."""

    serializer_class = ProductSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        return filter_products(Product.objects.select_related("category", "unit"), self.request.query_params)

    def _audit_fields(self, serializer):
        return [name for name in serializer.fields if name in {f.name for f in Product._meta.fields}]

    def perform_create(self, serializer):
        with transaction.atomic():
            product = serializer.save(created_by=self.request.user, updated_by=self.request.user)
            log_action(
                AuditLog.Action.CREATE,
                request=self.request,
                obj=product,
                changes=diff_snapshots({}, model_snapshot(product, self._audit_fields(serializer))),
                message="Alta vía API",
            )

    def perform_update(self, serializer):
        fields = self._audit_fields(serializer)
        with transaction.atomic():
            before = model_snapshot(Product.objects.select_for_update().get(pk=serializer.instance.pk), fields)
            product = serializer.save(updated_by=self.request.user)
            changes = diff_snapshots(before, model_snapshot(product, fields))
            if changes:
                log_action(
                    AuditLog.Action.UPDATE, request=self.request, obj=product, changes=changes, message="Vía API"
                )

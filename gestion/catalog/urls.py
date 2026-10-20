from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("productos/", views.ProductListView.as_view(), name="product_list"),
    path("productos/nuevo/", views.ProductCreateView.as_view(), name="product_create"),
    path("productos/exportar/", views.ProductExportView.as_view(), name="product_export"),
    path("productos/importar/", views.ProductImportView.as_view(), name="product_import"),
    path("productos/importar/plantilla/", views.ProductImportTemplateView.as_view(), name="product_import_template"),
    path("productos/importar/vista-previa/", views.ProductImportPreviewView.as_view(), name="product_import_preview"),
    path("productos/<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("productos/<int:pk>/editar/", views.ProductUpdateView.as_view(), name="product_update"),
    path("productos/<int:pk>/estado/", views.ProductToggleActiveView.as_view(), name="product_toggle_active"),
    path("categorias/", views.CategoryListView.as_view(), name="category_list"),
    path("categorias/nueva/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categorias/<int:pk>/editar/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("unidades/", views.UnitListView.as_view(), name="unit_list"),
    path("unidades/nueva/", views.UnitCreateView.as_view(), name="unit_create"),
    path("unidades/<int:pk>/editar/", views.UnitUpdateView.as_view(), name="unit_update"),
]

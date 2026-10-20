from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.StockListView.as_view(), name="stock_list"),
    path("exportar/", views.StockExportView.as_view(), name="stock_export"),
    path("existencias/<int:pk>/", views.StockUpdateView.as_view(), name="stock_update"),
    path("movimientos/", views.MovementListView.as_view(), name="movement_list"),
    path("movimientos/nuevo/", views.MovementCreateView.as_view(), name="movement_create"),
    path("movimientos/<int:pk>/", views.MovementDetailView.as_view(), name="movement_detail"),
    path("movimientos/<int:pk>/cancelar/", views.MovementReverseView.as_view(), name="movement_reverse"),
    path("ajustes/nuevo/", views.AdjustmentCreateView.as_view(), name="adjustment_create"),
    path("transferencias/nueva/", views.TransferCreateView.as_view(), name="transfer_create"),
    path("almacenes/", views.WarehouseListView.as_view(), name="warehouse_list"),
    path("almacenes/nuevo/", views.WarehouseCreateView.as_view(), name="warehouse_create"),
    path("almacenes/<int:pk>/", views.WarehouseDetailView.as_view(), name="warehouse_detail"),
    path("almacenes/<int:pk>/editar/", views.WarehouseUpdateView.as_view(), name="warehouse_update"),
    path("almacenes/<int:pk>/ubicaciones/", views.LocationCreateView.as_view(), name="location_create"),
]

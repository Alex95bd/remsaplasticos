from django.urls import path

from . import views

app_name = "pricing"

urlpatterns = [
    path("", views.PriceListListView.as_view(), name="pricelist_list"),
    path("nueva/", views.PriceListCreateView.as_view(), name="pricelist_create"),
    path("dictado/", views.DictationView.as_view(), name="dictation"),
    path("<int:pk>/", views.PriceListDetailView.as_view(), name="pricelist_detail"),
    path("<int:pk>/editar/", views.PriceListUpdateView.as_view(), name="pricelist_update"),
    path("<int:pk>/precios/", views.PriceItemSetView.as_view(), name="item_set"),
    path("<int:pk>/precios/<int:item_pk>/eliminar/", views.PriceItemDeleteView.as_view(), name="item_delete"),
    path("<int:pk>/exportar/<str:fmt>/", views.PriceListExportView.as_view(), name="export"),
]

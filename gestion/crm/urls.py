from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.PartyListView.as_view(), name="party_list"),
    path("nuevo/", views.PartyCreateView.as_view(), name="party_create"),
    path("<int:pk>/", views.PartyDetailView.as_view(), name="party_detail"),
    path("<int:pk>/editar/", views.PartyUpdateView.as_view(), name="party_update"),
    path("<int:pk>/estado/", views.PartyToggleActiveView.as_view(), name="party_toggle_active"),
]

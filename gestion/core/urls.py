from django.contrib.auth import views as auth_views
from django.urls import path

from accounts.views import LoginView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("salud/", views.health, name="health"),
]

auth_urlpatterns = [
    path("entrar/", LoginView.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
]

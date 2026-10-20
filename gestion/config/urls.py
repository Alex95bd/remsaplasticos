from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.urls import auth_urlpatterns

admin.site.site_header = "REMSA Gestión Comercial · Administración técnica"
admin.site.site_title = "REMSA Gestión"

urlpatterns = [
    path("", include("core.urls")),
    *auth_urlpatterns,
    path("cuentas/", include("accounts.urls")),
    path("catalogo/", include("catalog.urls")),
    path("clientes/", include("crm.urls")),
    path("cotizaciones/", include("quotes.urls")),
    path("bitacora/", include("audit.urls")),
    path("api/v1/", include("config.api_urls")),
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
]

handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"

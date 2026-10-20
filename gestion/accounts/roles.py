"""Definición de los roles del sistema.

Cada rol es un ``Group`` de Django. Los permisos se definen aquí (fuente oficial)
y se sincronizan automáticamente después de cada ``migrate`` o con
``python manage.py sync_roles``. Para agregar permisos a un rol edita este archivo.

Un permiso se escribe como ``"app_label.codename"``; ``"app_label.*"`` otorga
todos los permisos de la aplicación.
"""

from django.contrib.auth.models import Group, Permission

ROLE_ADMIN = "Administrador"
ROLE_SALES = "Ventas"
ROLE_WAREHOUSE = "Almacén"
ROLE_READONLY = "Consulta"

CATALOG_READ = [
    "catalog.view_product",
    "catalog.view_category",
    "catalog.view_unitofmeasure",
]

CRM_READ = ["crm.view_party"]
QUOTES_READ = ["quotes.view_quote", "quotes.view_quoteitem", "quotes.view_quotefollowup"]

ROLE_PERMISSIONS = {
    ROLE_ADMIN: [
        "accounts.*",
        "catalog.*",
        "crm.*",
        "quotes.*",
        "audit.view_auditlog",
        "auth.view_group",
    ],
    ROLE_SALES: CATALOG_READ
    + CRM_READ
    + QUOTES_READ
    + [
        "catalog.view_reference_price",
        "catalog.export_product",
        "crm.add_party",
        "crm.change_party",
        "quotes.add_quote",
        "quotes.change_quote",
        "quotes.add_quotefollowup",
    ],
    ROLE_WAREHOUSE: CATALOG_READ + CRM_READ,
    ROLE_READONLY: CATALOG_READ + CRM_READ + QUOTES_READ,
}

ROLE_DESCRIPTIONS = {
    ROLE_ADMIN: "Acceso completo: usuarios, catálogo, clientes, cotizaciones y bitácora.",
    ROLE_SALES: "Clientes y cotizaciones propias; catálogo con precios de referencia y exportación.",
    ROLE_WAREHOUSE: "Consulta del catálogo sin precios y del directorio de clientes/proveedores.",
    ROLE_READONLY: "Solo lectura: catálogo sin precios, clientes y cotizaciones.",
}

ROLE_NAMES = list(ROLE_PERMISSIONS)


def resolve_permissions(specs, using="default"):
    """Convierte la lista de especificaciones en permisos existentes y devuelve los faltantes."""
    perms = Permission.objects.using(using).select_related("content_type")
    found, missing = set(), []
    for spec in specs:
        app_label, codename = spec.split(".", 1)
        if codename == "*":
            matches = list(perms.filter(content_type__app_label=app_label))
        else:
            matches = list(perms.filter(content_type__app_label=app_label, codename=codename))
        if matches:
            found.update(matches)
        else:
            missing.append(spec)
    return found, missing


def sync_roles(using="default"):
    """Crea los grupos de rol y deja exactamente los permisos definidos en ``ROLE_PERMISSIONS``."""
    report = {}
    for role, specs in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.using(using).get_or_create(name=role)
        perms, missing = resolve_permissions(specs, using=using)
        group.permissions.set(perms)
        report[role] = {"permissions": len(perms), "missing": missing}
    return report


def role_groups():
    return Group.objects.filter(name__in=ROLE_NAMES).order_by("name")

from django.apps import AppConfig
from django.db.models.signals import post_migrate

PROJECT_APPS = {
    "core",
    "accounts",
    "catalog",
    "audit",
    "crm",
    "quotes",
    "inventory",
    "pricing",
    "agenda",
    "integrations",
}


def _sync_roles_after_migrate(sender, using="default", **kwargs):
    if sender.name not in PROJECT_APPS:
        return
    from .roles import sync_roles

    sync_roles(using=using)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Usuarios y permisos"

    def ready(self):
        post_migrate.connect(_sync_roles_after_migrate, dispatch_uid="accounts_sync_roles")

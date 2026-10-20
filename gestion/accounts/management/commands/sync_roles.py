from django.core.management.base import BaseCommand

from accounts.roles import sync_roles


class Command(BaseCommand):
    help = "Crea o actualiza los roles (grupos) y sus permisos según accounts/roles.py."

    def handle(self, *args, **options):
        for role, info in sync_roles().items():
            self.stdout.write(self.style.SUCCESS(f"{role}: {info['permissions']} permisos"))
            for spec in info["missing"]:
                self.stdout.write(self.style.WARNING(f"  Permiso no encontrado: {spec}"))

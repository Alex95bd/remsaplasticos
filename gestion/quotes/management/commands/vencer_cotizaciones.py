from django.core.management.base import BaseCommand

from quotes.services import expire_overdue


class Command(BaseCommand):
    help = "Marca como vencidas las cotizaciones enviadas o en seguimiento cuya vigencia terminó (programar a diario)."

    def handle(self, *args, **options):
        self.stdout.write(f"Cotizaciones vencidas: {expire_overdue()}")

from django.db import migrations

BASE_UNITS = [
    ("PZA", "Pieza"),
    ("MIL", "Millar"),
    ("CJA", "Caja"),
    ("PAQ", "Paquete"),
    ("TAR", "Tarima"),
    ("KG", "Kilogramo"),
    ("LT", "Litro"),
    ("SERV", "Servicio"),
]


def create_units(apps, schema_editor):
    UnitOfMeasure = apps.get_model("catalog", "UnitOfMeasure")
    for code, name in BASE_UNITS:
        UnitOfMeasure.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]

    operations = [migrations.RunPython(create_units, migrations.RunPython.noop)]

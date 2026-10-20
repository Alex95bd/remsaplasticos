from django.db import models


class Currency(models.TextChoices):
    MXN = "MXN", "Peso mexicano (MXN)"
    USD = "USD", "Dólar estadounidense (USD)"

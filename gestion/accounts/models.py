from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("correo electrónico", unique=True)
    job_title = models.CharField("puesto", max_length=120, blank=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name} ({self.username})" if full_name else self.username

    @property
    def role_names(self):
        return [group.name for group in self.groups.all()]

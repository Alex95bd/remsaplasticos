from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    """Registro de solo inserción de las acciones relevantes del sistema."""

    class Action(models.TextChoices):
        LOGIN = "login", "Inicio de sesión"
        LOGOUT = "logout", "Cierre de sesión"
        LOGIN_FAILED = "login_failed", "Inicio de sesión fallido"
        CREATE = "create", "Alta"
        UPDATE = "update", "Modificación"
        ACTIVATE = "activate", "Activación"
        DEACTIVATE = "deactivate", "Desactivación"
        IMPORT = "import", "Importación"
        EXPORT = "export", "Exportación"
        PASSWORD_CHANGE = "password_change", "Cambio de contraseña"
        PASSWORD_SET = "password_set", "Contraseña asignada por administrador"
        PASSWORD_RESET = "password_reset", "Recuperación de contraseña"
        STATUS_CHANGE = "status_change", "Cambio de estado"
        DUPLICATE = "duplicate", "Duplicado"
        PRINT = "print", "Impresión / PDF"
        MOVEMENT = "movement", "Movimiento de inventario"
        PRICE_CHANGE = "price_change", "Cambio de precios"
        SYNC = "sync", "Sincronización"

    created_at = models.DateTimeField("fecha", auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    username = models.CharField("nombre de usuario", max_length=150, blank=True)
    action = models.CharField("acción", max_length=30, choices=Action.choices, db_index=True)
    content_type = models.ForeignKey(
        ContentType, verbose_name="tipo de registro", on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.CharField("id del registro", max_length=64, blank=True)
    object_repr = models.CharField("registro", max_length=200, blank=True)
    message = models.CharField("detalle", max_length=255, blank=True)
    changes = models.JSONField("cambios", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    user_agent = models.CharField("navegador", max_length=255, blank=True)

    class Meta:
        verbose_name = "registro de bitácora"
        verbose_name_plural = "bitácora"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["content_type", "object_id"], name="audit_object_idx")]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} · {self.username or 'sistema'} · {self.get_action_display()}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("La bitácora es de solo inserción: no se pueden modificar registros.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("La bitácora es de solo inserción: no se pueden eliminar registros.")

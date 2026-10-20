from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AuditLog
from .services import log_action


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_action(AuditLog.Action.LOGIN, request=request, user=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        log_action(AuditLog.Action.LOGOUT, request=request, user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    # Django ya oculta la contraseña en ``credentials``; solo se guarda el usuario intentado.
    username = str(credentials.get("username", ""))[:150]
    log_action(AuditLog.Action.LOGIN_FAILED, request=request, username=username, message="Credenciales inválidas")

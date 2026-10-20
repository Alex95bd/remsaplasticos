from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin as DjangoPermissionRequiredMixin
from django.db import transaction
from django.shortcuts import redirect

from audit.models import AuditLog
from audit.services import diff_snapshots, log_action, model_snapshot


class PermissionRequiredMixin(DjangoPermissionRequiredMixin):
    """Valida permisos en el servidor y responde 403 a usuarios autenticados sin permiso."""

    raise_exception = True


class AuditedModelFormMixin:
    """Guarda el formulario en una transacción, asigna usuario y registra en la bitácora."""

    success_message = "Cambios guardados correctamente."

    def get_audit_fields(self, form):
        return list(form.fields)

    def form_valid(self, form):
        instance = form.instance
        is_new = instance._state.adding
        fields = self.get_audit_fields(form)
        before = {} if is_new else model_snapshot(instance._meta.model.objects.get(pk=instance.pk), fields)
        with transaction.atomic():
            obj = form.save(commit=False)
            if is_new and hasattr(obj, "created_by_id"):
                obj.created_by = self.request.user
            if hasattr(obj, "updated_by_id"):
                obj.updated_by = self.request.user
            obj.save()
            form.save_m2m()
            changes = diff_snapshots(before, model_snapshot(obj, fields))
            if is_new or changes:
                log_action(
                    AuditLog.Action.CREATE if is_new else AuditLog.Action.UPDATE,
                    request=self.request,
                    obj=obj,
                    changes=changes,
                )
        self.object = obj
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

"""Punto de extensión para un servicio externo de transcripción de audio.

Por defecto NO hay servicio conectado: el dictado usa la Web Speech API del navegador
o la captura de texto. Para conectar un proveedor (p. ej. un servicio de voz a texto
autorizado por la empresa) implementa ``TranscriptionBackend`` y define
``PRICING_TRANSCRIPTION_BACKEND`` con la ruta de la clase en ``.env``.
"""

from django.conf import settings
from django.utils.module_loading import import_string


class TranscriptionBackend:
    def transcribe(self, audio_file, language="es-MX") -> str:  # pragma: no cover - interfaz
        raise NotImplementedError


def get_backend():
    path = getattr(settings, "PRICING_TRANSCRIPTION_BACKEND", "")
    return import_string(path)() if path else None

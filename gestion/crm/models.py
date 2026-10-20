import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from core.models import UserStampedModel

RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
GENERIC_RFCS = {"XAXX010101000", "XEXX010101000"}


def normalize_rfc(value):
    return re.sub(r"[\s-]", "", value or "").upper()


def normalize_name(value):
    return " ".join((value or "").split())


class Party(UserStampedModel):
    """Cliente o proveedor (persona física o moral)."""

    class PartyType(models.TextChoices):
        CUSTOMER = "cliente", "Cliente"
        SUPPLIER = "proveedor", "Proveedor"
        BOTH = "ambos", "Cliente y proveedor"

    class PersonType(models.TextChoices):
        MORAL = "moral", "Persona moral"
        FISICA = "fisica", "Persona física"

    party_type = models.CharField("tipo de registro", max_length=10, choices=PartyType.choices)
    person_type = models.CharField("tipo de persona", max_length=10, choices=PersonType.choices, default="moral")
    name = models.CharField("nombre o razón social", max_length=200)
    trade_name = models.CharField("nombre comercial", max_length=200, blank=True)
    rfc = models.CharField("RFC", max_length=13, blank=True, help_text="12 caracteres (moral) o 13 (física).")
    contact_name = models.CharField("contacto principal", max_length=150, blank=True)
    contact_position = models.CharField("puesto del contacto", max_length=100, blank=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("correo", blank=True)
    fiscal_address = models.TextField("dirección fiscal", blank=True)
    fiscal_postal_code = models.CharField("C.P. fiscal", max_length=5, blank=True)
    tax_regime = models.CharField("régimen fiscal", max_length=100, blank=True)
    commercial_address = models.TextField("dirección comercial / entrega", blank=True)
    payment_terms_days = models.PositiveIntegerField("días de crédito", default=0)
    credit_limit = models.DecimalField(
        "límite de crédito", max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    commercial_conditions = models.TextField("condiciones comerciales", blank=True)
    notes = models.TextField("notas internas", blank=True)
    is_active = models.BooleanField("activo", default=True)
    external_code = models.CharField("código externo (Intelisis)", max_length=50, blank=True)

    class Meta:
        verbose_name = "cliente / proveedor"
        verbose_name_plural = "clientes y proveedores"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_code"], condition=~models.Q(external_code=""), name="crm_party_external_code_unique"
            ),
        ]
        indexes = [
            models.Index(fields=["party_type", "is_active"], name="crm_party_type_idx"),
            models.Index(fields=["rfc"], name="crm_party_rfc_idx"),
            models.Index(Lower("name"), name="crm_party_name_idx"),
        ]

    def __str__(self):
        return self.name

    @property
    def is_customer(self):
        return self.party_type in (self.PartyType.CUSTOMER, self.PartyType.BOTH)

    def clean(self):
        self.name = normalize_name(self.name)
        self.rfc = normalize_rfc(self.rfc)
        self.email = (self.email or "").strip().lower()
        if self.rfc:
            if not RFC_RE.match(self.rfc):
                raise ValidationError({"rfc": "RFC con formato inválido."})
            expected = 12 if self.person_type == self.PersonType.MORAL else 13
            if self.rfc not in GENERIC_RFCS and len(self.rfc) != expected:
                kind = self.get_person_type_display().lower()
                raise ValidationError({"rfc": f"Una {kind} usa RFC de {expected} caracteres."})
        if self.fiscal_postal_code and not re.fullmatch(r"\d{5}", self.fiscal_postal_code):
            raise ValidationError({"fiscal_postal_code": "El código postal debe tener 5 dígitos."})
        self.validate_duplicates()

    def duplicate_candidates(self):
        """Registros que chocan con este según ``settings.CRM_DUPLICATE_RULES``."""
        rules = {rule.strip().lower() for rule in settings.CRM_DUPLICATE_RULES}
        others = Party.objects.exclude(pk=self.pk)
        found = {}
        if "rfc" in rules and self.rfc and self.rfc not in GENERIC_RFCS:
            found["rfc"] = others.filter(rfc=self.rfc).first()
        if "nombre" in rules and self.name:
            found["name"] = others.filter(name__iexact=self.name).first()
        if "correo" in rules and self.email:
            found["email"] = others.filter(email__iexact=self.email).first()
        return {field: party for field, party in found.items() if party}

    def validate_duplicates(self):
        errors = {
            field: f"Ya existe un registro con este dato: {party.name}."
            for field, party in self.duplicate_candidates().items()
        }
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.rfc = normalize_rfc(self.rfc)
        self.name = normalize_name(self.name)
        super().save(*args, **kwargs)

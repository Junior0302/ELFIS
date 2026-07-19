from __future__ import annotations

import re

from app.services.contacts.errors import InvalidContactDataError
from app.services.contacts.normalize import digits_only, normalize_email, normalize_vat

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
_BIC_RE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")
_FR_VAT_RE = re.compile(r"^FR[A-Z0-9]{2}\d{9}$")


def clean_siren(value: str | None) -> str:
    return digits_only(value)[:9]


def clean_siret(value: str | None) -> str:
    return digits_only(value)[:14]


def validate_optional_identifiers(data: dict) -> dict:
    """Nettoie et valide les identifiants optionnels. Lève si format invalide."""
    out = dict(data)
    siren = clean_siren(out.get("siren"))
    siret = clean_siret(out.get("siret"))
    vat = normalize_vat(out.get("vat_number"))
    email = normalize_email(out.get("email"))
    iban = re.sub(r"\s+", "", (out.get("iban") or "").upper())
    bic = re.sub(r"\s+", "", (out.get("bic") or "").upper())

    if siren and len(siren) != 9:
        raise InvalidContactDataError("SIREN invalide (9 chiffres attendus)")
    if siret and len(siret) != 14:
        raise InvalidContactDataError("SIRET invalide (14 chiffres attendus)")
    if siret and siren and not siret.startswith(siren):
        raise InvalidContactDataError("SIRET incohérent avec le SIREN")
    if siret and not siren:
        siren = siret[:9]
    if email and not _EMAIL_RE.match(email):
        raise InvalidContactDataError("Adresse e-mail invalide")
    if iban and not _IBAN_RE.match(iban):
        raise InvalidContactDataError("IBAN invalide")
    if bic and not _BIC_RE.match(bic):
        raise InvalidContactDataError("BIC invalide")
    if vat and vat.startswith("FR") and not _FR_VAT_RE.match(vat):
        raise InvalidContactDataError("Numéro de TVA française invalide")

    out["siren"] = siren
    out["siret"] = siret
    out["vat_number"] = vat
    out["email"] = email
    out["iban"] = iban
    out["bic"] = bic
    out["phone"] = (out.get("phone") or "").strip()
    out["company_name"] = (out.get("company_name") or "").strip()
    out["first_name"] = (out.get("first_name") or "").strip()
    out["last_name"] = (out.get("last_name") or "").strip()
    out["address_line_1"] = (out.get("address_line_1") or out.get("address") or "").strip()
    out["postal_code"] = (out.get("postal_code") or "").strip()
    out["city"] = (out.get("city") or "").strip()
    out["country"] = (out.get("country") or "France").strip() or "France"
    return out


def require_minimal_identity(data: dict) -> None:
    company = (data.get("company_name") or "").strip()
    person = (data.get("first_name") or "").strip() or (data.get("last_name") or "").strip()
    if not company and not person:
        raise InvalidContactDataError("Indiquez au moins un nom d’entreprise ou un nom de personne")

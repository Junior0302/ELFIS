from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.models_saas import Organization, SalesDocument

PREMIUM_TEMPLATE = "premium_v1"


@dataclass(frozen=True)
class DocumentBrandProfile:
    """Profil d’identité pour PDF commerciaux (factures, devis, avoirs, etc.)."""

    display_name: str
    legal_name: str
    siren: str
    vat_number: str
    address_line: str
    postal_code: str
    city: str
    country: str
    phone: str
    email: str
    website: str
    iban: str
    bic: str
    share_capital: str
    legal_form: str
    legal_mentions: str
    logo_url: str
    logo_path: Path | None
    primary_color: str
    secondary_color: str
    documents_show_logo: bool | None = None

    @property
    def has_logo(self) -> bool:
        return self.logo_path is not None and self.logo_path.is_file()

    @property
    def org_name_strong(self) -> str:
        return (self.legal_name or self.display_name or "").strip()

    def address_block_lines(self) -> list[str]:
        lines: list[str] = []
        name = self.org_name_strong
        if name:
            lines.append(name)
        if self.legal_form.strip():
            lines.append(self.legal_form.strip())
        if self.address_line.strip():
            lines.append(self.address_line.strip())
        city_line = " ".join(part for part in [self.postal_code.strip(), self.city.strip()] if part)
        if city_line:
            lines.append(city_line)
        if self.country.strip() and self.country.strip().upper() not in {"FR", "FRA", "FRANCE"}:
            lines.append(self.country.strip())
        return lines

    def contact_lines(self) -> list[str]:
        lines: list[str] = []
        if self.phone.strip():
            lines.append(f"Tél. {self.phone.strip()}")
        if self.email.strip():
            lines.append(self.email.strip())
        if self.website.strip():
            lines.append(self.website.strip())
        return lines

    def legal_id_lines(self) -> list[str]:
        lines: list[str] = []
        if self.siren.strip():
            label = "SIRET" if len(self.siren.strip()) >= 14 else "SIREN"
            lines.append(f"{label} {self.siren.strip()}")
        if self.vat_number.strip():
            lines.append(f"TVA {self.vat_number.strip()}")
        if self.share_capital.strip():
            lines.append(f"Capital {self.share_capital.strip()}")
        return lines

    def bank_lines(self) -> list[str]:
        lines: list[str] = []
        if self.iban.strip():
            lines.append(f"IBAN {self.iban.strip()}")
        if self.bic.strip():
            lines.append(f"BIC {self.bic.strip()}")
        return lines

    def footer_parts(self) -> list[str]:
        parts: list[str] = []
        name = self.org_name_strong
        if name:
            parts.append(name)
        city_line = " ".join(part for part in [self.postal_code.strip(), self.city.strip()] if part)
        addr = ", ".join(
            part
            for part in [self.address_line.strip(), city_line, self.country.strip() or None]
            if part
        )
        if addr:
            parts.append(addr)
        parts.extend(self.contact_lines())
        parts.extend(self.legal_id_lines())
        parts.extend(self.bank_lines())
        if self.legal_mentions.strip():
            parts.append(self.legal_mentions.strip())
        return parts


@dataclass(frozen=True)
class DocumentRenderConfig:
    """Source unique de config documentaire (preview / PDF / email / Vault)."""

    brand: DocumentBrandProfile
    show_logo: bool
    template: str = PREMIUM_TEMPLATE

    @property
    def render_logo(self) -> bool:
        return self.show_logo and self.brand.has_logo

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "showLogo": self.show_logo,
            "template": self.template,
            "hasLogoFile": self.brand.has_logo,
            "logoUrl": self.brand.logo_url or "",
            "primaryColor": self.brand.primary_color,
            "secondaryColor": self.brand.secondary_color,
            "displayName": self.brand.display_name,
            "legalName": self.brand.legal_name,
        }


def _resolve_logo_path(logo_url: str) -> Path | None:
    raw = (logo_url or "").strip()
    if not raw:
        return None
    # URL locale servie par l’API
    marker = "/api/org/logos/"
    if marker in raw:
        filename = Path(urlparse(raw).path).name
        logos = settings.storage_path / "logos"
        # Préférer la miniature (toujours raster) pour le PDF
        thumb = logos / f"thumb_{filename}"
        if thumb.is_file():
            return thumb
        path = logos / filename
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return path
        # SVG sans miniature : ReportLab ne l’embarque pas → raison sociale seule
        return None
    # Chemin absolu local (tests / legacy)
    candidate = Path(raw)
    if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return candidate
    return None


def brand_from_organization(organization: Organization | None) -> DocumentBrandProfile:
    if organization is None:
        return DocumentBrandProfile(
            display_name="",
            legal_name="",
            siren="",
            vat_number="",
            address_line="",
            postal_code="",
            city="",
            country="",
            phone="",
            email="",
            website="",
            iban="",
            bic="",
            share_capital="",
            legal_form="",
            legal_mentions="",
            logo_url="",
            logo_path=None,
            primary_color="#0B3D2E",
            secondary_color="#E7F2EC",
            documents_show_logo=None,
        )

    logo_url = (organization.logo or "").strip()
    primary = (getattr(organization, "primary_color", None) or "").strip() or "#0B3D2E"
    secondary = (getattr(organization, "secondary_color", None) or "").strip() or "#E7F2EC"
    pref = getattr(organization, "documents_show_logo", None)
    return DocumentBrandProfile(
        display_name=(organization.name or "").strip(),
        legal_name=(organization.legal_name or "").strip(),
        siren=(organization.siren or "").strip(),
        vat_number=(organization.vat_number or "").strip(),
        address_line=(organization.address or "").strip(),
        postal_code=(getattr(organization, "postal_code", None) or "").strip(),
        city=(getattr(organization, "city", None) or "").strip(),
        country=(organization.country or "").strip(),
        phone=(getattr(organization, "phone", None) or "").strip(),
        email=(getattr(organization, "email", None) or "").strip(),
        website=(getattr(organization, "website", None) or "").strip(),
        iban=(getattr(organization, "iban", None) or "").strip(),
        bic=(getattr(organization, "bic", None) or "").strip(),
        share_capital=(getattr(organization, "share_capital", None) or "").strip(),
        legal_form=(getattr(organization, "legal_form", None) or "").strip(),
        legal_mentions=(getattr(organization, "legal_mentions", None) or "").strip(),
        logo_url=logo_url,
        logo_path=_resolve_logo_path(logo_url),
        primary_color=primary if primary.startswith("#") else "#0B3D2E",
        secondary_color=secondary if secondary.startswith("#") else "#E7F2EC",
        documents_show_logo=pref if isinstance(pref, bool) else None,
    )


def parse_document_branding(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw or "{}")
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    out: dict[str, Any] = {}
    if "showLogo" in data:
        out["showLogo"] = bool(data["showLogo"])
    elif "show_logo" in data:
        out["showLogo"] = bool(data["show_logo"])
    template = (data.get("template") or PREMIUM_TEMPLATE)
    if isinstance(template, str) and template.strip():
        out["template"] = template.strip()
    else:
        out["template"] = PREMIUM_TEMPLATE
    return out


def dump_document_branding(*, show_logo: bool, template: str = PREMIUM_TEMPLATE) -> str:
    return json.dumps(
        {"showLogo": bool(show_logo), "template": template or PREMIUM_TEMPLATE},
        ensure_ascii=False,
    )


def resolve_show_logo(
    *,
    document_branding: dict[str, Any] | None,
    brand: DocumentBrandProfile,
) -> bool:
    """Default : préférence org si existe, sinon Avec si logo PDF-safe, sinon Sans."""
    if document_branding and "showLogo" in document_branding:
        return bool(document_branding["showLogo"])
    if brand.documents_show_logo is not None:
        return bool(brand.documents_show_logo)
    return bool(brand.has_logo)


def render_config_for_document(
    doc: SalesDocument | None,
    organization: Organization | None,
) -> DocumentRenderConfig:
    brand = brand_from_organization(organization)
    parsed = parse_document_branding(getattr(doc, "branding_json", None) if doc else None)
    show = resolve_show_logo(document_branding=parsed, brand=brand)
    template = str(parsed.get("template") or PREMIUM_TEMPLATE)
    return DocumentRenderConfig(brand=brand, show_logo=show, template=template)

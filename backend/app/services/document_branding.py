from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.config import settings
from app.models_saas import Organization


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

    @property
    def has_logo(self) -> bool:
        return self.logo_path is not None and self.logo_path.is_file()

    def address_block_lines(self) -> list[str]:
        lines: list[str] = []
        name = (self.legal_name or self.display_name or "").strip()
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
        name = (self.legal_name or self.display_name or "").strip()
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
        )

    logo_url = (organization.logo or "").strip()
    primary = (getattr(organization, "primary_color", None) or "").strip() or "#0B3D2E"
    secondary = (getattr(organization, "secondary_color", None) or "").strip() or "#E7F2EC"
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
    )

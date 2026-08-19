"""Taxonomie documentaire ELFIS — registre unique (code, pas de mutation API)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentTypeDef:
    key: str
    label: str
    category: str
    description: str
    allowed_mime_types: tuple[str, ...] = ()
    expected_sources: tuple[str, ...] = ()
    sensitive: bool = False
    processing_policy: str = "standard"
    aliases: tuple[str, ...] = ()


class DocumentTypeRegistry:
    """Source unique de vérité pour les types documentaires ELFIS."""

    def __init__(self, types: tuple[DocumentTypeDef, ...] | None = None) -> None:
        self._by_key: dict[str, DocumentTypeDef] = {}
        self._alias_to_key: dict[str, str] = {}
        for t in types or DEFAULT_DOCUMENT_TYPES:
            self.register(t)

    def register(self, type_def: DocumentTypeDef) -> None:
        self._by_key[type_def.key] = type_def
        self._alias_to_key[type_def.key.lower()] = type_def.key
        for alias in type_def.aliases:
            self._alias_to_key[alias.lower().strip()] = type_def.key

    def get(self, key: str) -> DocumentTypeDef | None:
        if not key:
            return None
        resolved = self._alias_to_key.get(key.lower().strip())
        if not resolved:
            return None
        return self._by_key.get(resolved)

    def resolve_key(self, key_or_alias: str) -> str | None:
        t = self.get(key_or_alias)
        return t.key if t else None

    def is_known(self, key: str) -> bool:
        return self.get(key) is not None

    def list_types(self) -> list[DocumentTypeDef]:
        return sorted(self._by_key.values(), key=lambda t: t.key)

    def keys(self) -> list[str]:
        return sorted(self._by_key.keys())


DEFAULT_DOCUMENT_TYPES: tuple[DocumentTypeDef, ...] = (
    DocumentTypeDef(
        key="supplier_invoice",
        label="Facture fournisseur",
        category="commercial",
        description="Facture émise par un fournisseur",
        allowed_mime_types=("application/pdf", "image/jpeg", "image/png"),
        aliases=("facture_fournisseur", "purchase_invoice"),
    ),
    DocumentTypeDef(
        key="customer_invoice",
        label="Facture client",
        category="commercial",
        description="Facture émise vers un client",
        allowed_mime_types=("application/pdf", "image/jpeg", "image/png"),
        aliases=("facture_client", "sales_invoice"),
    ),
    DocumentTypeDef(
        key="invoice",
        label="Facture (direction indéterminée)",
        category="commercial",
        description="Facture sans signal fiable fournisseur/client — revue recommandée",
        allowed_mime_types=("application/pdf", "image/jpeg", "image/png"),
        aliases=("facture",),
        processing_policy="requires_review",
    ),
    DocumentTypeDef(
        key="quote",
        label="Devis",
        category="commercial",
        description="Devis / proposition commerciale",
        allowed_mime_types=("application/pdf",),
        aliases=("devis", "quotation", "estimate"),
    ),
    DocumentTypeDef(
        key="purchase_order",
        label="Bon de commande",
        category="commercial",
        description="Bon de commande",
        aliases=("bon_commande", "po", "purchase-order"),
    ),
    DocumentTypeDef(
        key="delivery_note",
        label="Bon de livraison",
        category="commercial",
        description="Bon de livraison",
        aliases=("bon_livraison", "delivery", "bl"),
    ),
    DocumentTypeDef(
        key="credit_note",
        label="Avoir",
        category="commercial",
        description="Avoir / note de crédit",
        aliases=("avoir", "credit-note", "creditnote"),
    ),
    DocumentTypeDef(
        key="receipt",
        label="Reçu",
        category="expense",
        description="Reçu / ticket",
        aliases=("recu", "ticket"),
    ),
    DocumentTypeDef(
        key="expense_report",
        label="Note de frais",
        category="expense",
        description="Note de frais",
        aliases=("note_frais", "expense"),
    ),
    DocumentTypeDef(
        key="bank_statement",
        label="Relevé bancaire",
        category="finance",
        description="Relevé de compte bancaire",
        allowed_mime_types=(
            "application/pdf",
            "text/csv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        aliases=("releve", "relevé", "statement", "bank"),
        sensitive=True,
    ),
    DocumentTypeDef(
        key="contract",
        label="Contrat",
        category="legal",
        description="Contrat / accord",
        aliases=("contrat", "agreement"),
        sensitive=True,
        processing_policy="sensitive",
    ),
    DocumentTypeDef(
        key="payroll_document",
        label="Document paie",
        category="hr",
        description="Bulletin / document de paie",
        aliases=("bulletin", "payslip", "paie", "payroll"),
        sensitive=True,
        processing_policy="sensitive",
    ),
    DocumentTypeDef(
        key="identity_document",
        label="Pièce d'identité",
        category="identity",
        description="Document d'identité",
        aliases=("cni", "passeport", "identity", "id_card"),
        sensitive=True,
        processing_policy="sensitive",
    ),
    DocumentTypeDef(
        key="tax_document",
        label="Document fiscal",
        category="tax",
        description="Document fiscal / déclaration",
        aliases=("fiscal", "tax", "urssaf", "impot"),
        sensitive=True,
    ),
    DocumentTypeDef(
        key="supporting_document",
        label="Pièce justificative",
        category="other",
        description="Justificatif générique",
        aliases=("justificatif", "attachment", "supporting"),
    ),
    DocumentTypeDef(
        key="unknown",
        label="Inconnu",
        category="other",
        description="Type non déterminé",
        processing_policy="requires_review",
    ),
)

_REGISTRY: DocumentTypeRegistry | None = None


def get_document_type_registry() -> DocumentTypeRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DocumentTypeRegistry()
    return _REGISTRY

from __future__ import annotations

from typing import Literal

ModuleStatus = Literal["live", "setup"]

MODULES: list[dict] = [
    {
        "id": 1,
        "slug": "comptabilite",
        "name": "Comptabilité",
        "status": "live",
        "summary": "OCR, extraction, contrôles, écritures, FEC et exports logiciels.",
        "capabilities": [
            "gestion_factures",
            "ocr_pdf_photos",
            "detection_type",
            "extraction",
            "verification_montants",
            "incoherences",
            "imputation",
            "ecritures",
            "export_fec",
            "export_logiciels",
        ],
        "route": "/history",
    },
    {
        "id": 4,
        "slug": "facturation",
        "name": "Facturation",
        "status": "live",
        "summary": "Devis, factures, avoirs, suivi des paiements et relances.",
        "capabilities": ["devis", "factures", "avoirs", "relances", "paiements"],
        "route": "/facturation",
    },
    {
        "id": 6,
        "slug": "pilotage",
        "name": "Pilotage",
        "status": "live",
        "summary": "CA, marge, résultat, rentabilité, trésorerie, coûts, objectifs.",
        "capabilities": ["ca", "marge", "resultat", "rentabilite", "tresorerie", "objectifs"],
        "route": "/dashboard",
    },
    {
        "id": 8,
        "slug": "assistant",
        "name": "Assistant du dirigeant",
        "status": "live",
        "summary": "Questions en langage naturel sur l’entreprise.",
        "capabilities": ["qa_naturelle", "explications", "finance_agent"],
        "route": "/copilote",
    },
    {
        "id": 12,
        "slug": "previsions",
        "name": "Prévisions",
        "status": "live",
        "summary": "Simulations recrutement, véhicule, emprunt, agence.",
        "capabilities": ["simulations", "impact_financier"],
        "route": "/copilote",
    },
    {
        "id": 13,
        "slug": "multi-entreprises",
        "name": "Multi-entreprises",
        "status": "live",
        "summary": "Sociétés, établissements, devises, utilisateurs.",
        "capabilities": ["multi_societes", "devises", "utilisateurs"],
        "route": "/organisation",
    },
]


def get_modules() -> list[dict]:
    return MODULES


def get_module(slug: str) -> dict | None:
    for mod in MODULES:
        if mod["slug"] == slug:
            return mod
    return None

"""RuleOptimizer — propose des optimisations, jamais de modification automatique."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_intelligence.models import (
    ElfisAiFeedback,
    ElfisAiLearningMemory,
    ElfisAiRecommendationHistory,
)


class RuleOptimizer:
    """Détecte règles inutilisées, conflits, doublons, préférences obsolètes."""

    def __init__(self, db: Session):
        self._db = db

    def analyze(self, *, organization_id: int) -> dict[str, Any]:
        proposals: list[dict[str, Any]] = []

        memories = (
            self._db.query(ElfisAiLearningMemory)
            .filter(ElfisAiLearningMemory.organization_id == organization_id)
            .filter(ElfisAiLearningMemory.is_current.is_(True))
            .all()
        )
        # Doublons : mêmes comptes pour parties différentes
        by_accounts: dict[str, list[str]] = {}
        for m in memories:
            sig = "|".join(
                sorted(f"{k}:{v}" for k, v in (m.preferred_accounts_json or {}).items())
            )
            by_accounts.setdefault(sig, []).append(m.party_name or m.memory_key)
        for sig, parties in by_accounts.items():
            if sig and len(parties) >= 3:
                proposals.append(
                    {
                        "type": "duplicate_preference",
                        "severity": "low",
                        "message": (
                            f"Préférence de comptes identique pour {len(parties)} tiers — "
                            "envisager une règle générique (proposition seule)."
                        ),
                        "parties": parties[:10],
                    }
                )

        # Conflits : même party_name avec versions historiques contradictoires
        keys = {m.memory_key for m in memories}
        for key in keys:
            versions = (
                self._db.query(ElfisAiLearningMemory)
                .filter(ElfisAiLearningMemory.organization_id == organization_id)
                .filter(ElfisAiLearningMemory.memory_key == key)
                .order_by(ElfisAiLearningMemory.version.desc())
                .limit(5)
                .all()
            )
            if len(versions) < 2:
                continue
            a0 = versions[0].preferred_accounts_json or {}
            a1 = versions[1].preferred_accounts_json or {}
            if a0 and a1 and a0 != a1:
                proposals.append(
                    {
                        "type": "conflict",
                        "severity": "medium",
                        "message": (
                            f"Conflit d'apprentissage pour « {versions[0].party_name or key} » "
                            f"(v{versions[1].version} → v{versions[0].version})."
                        ),
                        "memory_key": key,
                    }
                )

        # Préférences obsolètes : pas de feedback accepté récent alors que recommandations divergent
        rejected = (
            self._db.query(ElfisAiFeedback)
            .filter(ElfisAiFeedback.organization_id == organization_id)
            .filter(ElfisAiFeedback.action == "reject")
            .count()
        )
        accepted = (
            self._db.query(ElfisAiFeedback)
            .filter(ElfisAiFeedback.organization_id == organization_id)
            .filter(ElfisAiFeedback.action == "accept")
            .count()
        )
        if rejected > accepted and rejected >= 3:
            proposals.append(
                {
                    "type": "obsolete_preference",
                    "severity": "high",
                    "message": (
                        "Taux de refus élevé — revoir les préférences mémorisées "
                        "(aucune modification automatique)."
                    ),
                    "rejected": rejected,
                    "accepted": accepted,
                }
            )

        # Règles / sources peu utilisées
        sources = Counter(
            r.primary_source
            for r in self._db.query(ElfisAiRecommendationHistory)
            .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
            .limit(200)
            .all()
            if r.primary_source
        )
        if sources and sources.get("rules", 0) == 0 and sum(sources.values()) >= 5:
            proposals.append(
                {
                    "type": "unused_rules",
                    "severity": "low",
                    "message": (
                        "Aucune recommandation issue de règles métier sur l'échantillon — "
                        "vérifier la configuration des règles."
                    ),
                }
            )

        return {
            "organization_id": organization_id,
            "optimizations": proposals,
            "auto_applied": False,
            "disclaimer": "Propositions d'optimisation uniquement — aucune règle modifiée automatiquement.",
        }

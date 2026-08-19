"""SimilarityEngine — score de similarité document / tiers / montants / TVA."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.models import ElfisAccountingEngineProposal
from app.accounting_intelligence.models import (
    ElfisAiLearningMemory,
    ElfisAiRecommendationHistory,
    ElfisAiSimilarityCache,
)


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _key_parts(**parts: Any) -> str:
    raw = "|".join(f"{k}={_norm(str(v)) if v is not None else ''}" for k, v in sorted(parts.items()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


@dataclass
class SimilarityMatch:
    candidate_key: str
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_key": self.candidate_key,
            "score": self.score,
            "factors": self.factors,
            "payload": self.payload,
        }


class SimilarityEngine:
    def __init__(self, db: Session):
        self._db = db

    def compare(
        self,
        *,
        query: dict[str, Any],
        candidate: dict[str, Any],
    ) -> SimilarityMatch:
        factors: dict[str, float] = {}
        weights = {
            "party": 0.30,
            "label": 0.15,
            "amount": 0.20,
            "vat": 0.15,
            "category": 0.10,
            "history": 0.10,
        }

        q_party = _norm(
            query.get("supplier_name") or query.get("customer_name") or query.get("party_name")
        )
        c_party = _norm(
            candidate.get("supplier_name")
            or candidate.get("customer_name")
            or candidate.get("party_name")
        )
        if q_party and c_party:
            if q_party == c_party:
                factors["party"] = 1.0
            elif q_party in c_party or c_party in q_party:
                factors["party"] = 0.7
            else:
                # token overlap
                qt, ct = set(q_party.split()), set(c_party.split())
                factors["party"] = len(qt & ct) / max(1, len(qt | ct))
        else:
            factors["party"] = 0.0

        q_label = _norm(query.get("label") or query.get("document_number") or "")
        c_label = _norm(candidate.get("label") or candidate.get("document_number") or "")
        if q_label and c_label:
            ql, cl = set(q_label.split()), set(c_label.split())
            factors["label"] = len(ql & cl) / max(1, len(ql | cl))
        else:
            factors["label"] = 0.3 if not q_label and not c_label else 0.0

        q_ttc = float(query.get("amount_ttc") or query.get("amount") or 0)
        c_ttc = float(candidate.get("amount_ttc") or candidate.get("amount") or 0)
        if q_ttc > 0 and c_ttc > 0:
            ratio = min(q_ttc, c_ttc) / max(q_ttc, c_ttc)
            factors["amount"] = ratio if ratio >= 0.5 else ratio * 0.5
        else:
            factors["amount"] = 0.2

        q_vat = query.get("vat_rate")
        c_vat = candidate.get("vat_rate")
        if q_vat is not None and c_vat is not None:
            factors["vat"] = 1.0 if float(q_vat) == float(c_vat) else 0.2
        else:
            factors["vat"] = 0.4

        q_cat = _norm(
            f"{query.get('direction') or ''}|{query.get('document_type') or ''}"
        )
        c_cat = _norm(
            f"{candidate.get('direction') or ''}|{candidate.get('document_type') or ''}"
        )
        factors["category"] = 1.0 if q_cat and q_cat == c_cat else (0.4 if q_cat and c_cat else 0.2)

        factors["history"] = float(candidate.get("history_boost") or 0.5)

        score = sum(weights[k] * factors.get(k, 0.0) for k in weights)
        return SimilarityMatch(
            candidate_key=_key_parts(
                party=c_party,
                doc=candidate.get("document_type"),
                dir=candidate.get("direction"),
            ),
            score=round(max(0.0, min(1.0, score)), 4),
            factors=factors,
            payload=candidate,
        )

    def find_similar(
        self,
        *,
        organization_id: int,
        query: dict[str, Any],
        limit: int = 5,
        use_cache: bool = True,
    ) -> list[SimilarityMatch]:
        q_key = _key_parts(
            party=query.get("supplier_name") or query.get("customer_name"),
            direction=query.get("direction"),
            document_type=query.get("document_type"),
            vat=query.get("vat_rate"),
            amount=query.get("amount_ttc"),
        )
        matches: list[SimilarityMatch] = []

        # Candidats : learning memory + recommendations + proposals
        candidates: list[dict[str, Any]] = []
        for mem in (
            self._db.query(ElfisAiLearningMemory)
            .filter(ElfisAiLearningMemory.organization_id == organization_id)
            .filter(ElfisAiLearningMemory.is_current.is_(True))
            .limit(50)
            .all()
        ):
            candidates.append(
                {
                    "party_name": mem.party_name,
                    "direction": mem.direction,
                    "document_type": mem.document_type,
                    "vat_rate": mem.vat_rate,
                    "history_boost": 0.95,
                    "accounts": mem.preferred_accounts_json or {},
                    "journal": mem.preferred_journal,
                    "source": "learning",
                }
            )
        for rec in (
            self._db.query(ElfisAiRecommendationHistory)
            .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
            .order_by(ElfisAiRecommendationHistory.created_at.desc())
            .limit(50)
            .all()
        ):
            snap = rec.input_snapshot_json or {}
            candidates.append(
                {
                    "party_name": rec.party_name,
                    "supplier_name": snap.get("supplier_name"),
                    "customer_name": snap.get("customer_name"),
                    "direction": rec.direction,
                    "document_type": rec.document_type,
                    "vat_rate": rec.vat_rate,
                    "amount_ttc": snap.get("amount_ttc"),
                    "document_number": snap.get("document_number"),
                    "history_boost": 0.7,
                    "accounts": {"expense_or_revenue": rec.account_code} if rec.account_code else {},
                    "journal": rec.journal_code,
                    "source": "recommendation",
                    "recommendation_id": rec.id,
                }
            )
        for prop in (
            self._db.query(ElfisAccountingEngineProposal)
            .filter(ElfisAccountingEngineProposal.organization_id == organization_id)
            .order_by(ElfisAccountingEngineProposal.created_at.desc())
            .limit(50)
            .all()
        ):
            snap = prop.input_snapshot_json or {}
            expense = None
            for line in prop.lines_json or []:
                label = (line.get("account_label") or "").lower()
                if "tva" not in label and "fournisseur" not in label and "client" not in label:
                    expense = line.get("account_code")
                    break
            candidates.append(
                {
                    "party_name": snap.get("supplier_name") or snap.get("customer_name"),
                    "supplier_name": snap.get("supplier_name"),
                    "customer_name": snap.get("customer_name"),
                    "direction": prop.direction,
                    "document_type": prop.document_type,
                    "vat_rate": prop.vat_rate,
                    "amount_ttc": prop.amount_ttc,
                    "document_number": snap.get("document_number"),
                    "history_boost": 0.6,
                    "accounts": {"expense_or_revenue": expense} if expense else {},
                    "journal": prop.journal_code,
                    "source": "proposal",
                    "proposal_id": prop.id,
                }
            )

        for cand in candidates:
            m = self.compare(query=query, candidate=cand)
            if m.score >= 0.35:
                matches.append(m)
                if use_cache:
                    self._cache_put(
                        organization_id=organization_id,
                        query_key=q_key,
                        match=m,
                    )

        matches.sort(key=lambda m: m.score, reverse=True)
        # dédup by candidate_key
        seen: set[str] = set()
        unique: list[SimilarityMatch] = []
        for m in matches:
            if m.candidate_key in seen:
                continue
            seen.add(m.candidate_key)
            unique.append(m)
            if len(unique) >= limit:
                break
        return unique

    def _cache_put(
        self, *, organization_id: int, query_key: str, match: SimilarityMatch
    ) -> None:
        row = (
            self._db.query(ElfisAiSimilarityCache)
            .filter(ElfisAiSimilarityCache.organization_id == organization_id)
            .filter(ElfisAiSimilarityCache.query_key == query_key)
            .filter(ElfisAiSimilarityCache.candidate_key == match.candidate_key)
            .first()
        )
        if not row:
            row = ElfisAiSimilarityCache(
                organization_id=organization_id,
                query_key=query_key,
                candidate_key=match.candidate_key,
            )
        row.score = match.score
        row.factors_json = match.factors
        row.payload_json = match.payload
        row.expires_at = datetime.utcnow() + timedelta(days=7)
        self._db.add(row)
        self._db.flush()

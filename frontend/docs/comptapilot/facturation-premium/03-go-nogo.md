# 03 — GO / NO GO Facturation Premium

**Date :** 2026-08-02

---

## GO — P0.5 UI premium (cette session)

| Décision | Raison |
|----------|--------|
| **GO** présentation premium `/facturation` | Pas de spec produit détaillée ; UI safe = seule suite Blueprint-compatible immédiate |
| **GO** docs sous `comptapilot/facturation-premium/` | Remplace le vide « non démarré » du Blueprint |
| **GO** réutiliser tokens / patterns FCC | Cohérence ComptaPilot sans nouveau Pilot |

---

## NO GO — immédiat

| Décision | Raison |
|----------|--------|
| **NO GO** S1.3 Relations | Explicitement hors Facturation (Blueprint roadmap) |
| **NO GO** nouveau Pilot / absorption Sales | Trois Lois |
| **NO GO** changer moteurs / calculs / API billing | Scope UI only |
| **NO GO** inventer forecasts / KPIs | Principe Dashboard Premium |
| **NO GO** Widget Framework forcé sur formulaire | Page opérationnelle ; widgets si future surface dashboard |

---

## Prochaines étapes recommandées

1. Validation visuelle manuelle `/facturation` (desktop + mobile ≤720px).
2. P0.6 : aligner `SalesDocPreviewModal` / empty states envoi (sans changer transport mail).
3. Brancher filtres `status` / `q` déjà supportés côté `billingOverview` **si** priorisé produit.
4. Relire commercial-readiness Vague 0 (SMTP) — chip SMTP reflète déjà `smtp_configured`.

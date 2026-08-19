# 02 — Plan P0.5 Facturation Premium (UI safe)

**Objectif :** élever `/facturation` au niveau de présence visuelle du Dashboard Premium **sans** changer API, calculs, ni flux métier.

Référence visuelle : [`../../dashboard-premium/01-overview.md`](../../dashboard-premium/01-overview.md)

---

## Périmètre P0.5 (GO)

1. **Header premium** — titre serif, lede, meta chips (source ComptaPilot, SMTP si connu, compteurs docs/impayés réels).
2. **Bandeau KPI** — 4 métriques existantes ; emphase visuelle sur **Montant dû** / Impayés.
3. **Sections** — « Créer », « Répartition », « Documents » avec rythme / surfaces FCC-like.
4. **Table & empty** — lisibilité, hover discret, empty state cohérent.
5. **Tokens** — navy / accent vert comptable, ombres légères, `prefers-reduced-motion`.
6. **Marqueur** — `data-billing-layout="fp05"`.
7. **Docs** — ce dossier + changelog.

## Hors périmètre P0.5 (NO GO)

- Nouveaux endpoints ou champs API
- Refonte modales preview / paiement / envoi
- Widget Framework complet (reporté si dashboard facturation)
- DevisPage premium (chantier séparé éventuel)
- S1.3 Relations

---

## Phases suivantes (après P0.5)

| Phase | Contenu | Prérequis |
|-------|---------|-----------|
| **P0.6** | Polish modales (preview / paiement) aligné DS | P0.5 stable |
| **P1** | Filtres statut + recherche UI (API déjà paramétrable) | Spec produit |
| **P1.b** | Empty / onboarding premium first-invoice | commercial-readiness |
| **P2** | Surface « suivi encaissements » éventuelle (widgets) | Ownership + Widget Framework |

---

## Critères d’acceptation P0.5

- [x] Aucun chiffre inventé ; seules stats `BillingOverview`
- [x] Toutes les actions métier existantes restent disponibles
- [x] Marqueur `data-billing-layout="fp05"` présent
- [x] Build + tests ciblés verts
- [x] GO/NO GO documenté

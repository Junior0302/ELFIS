# 01 — Audit runtime Facturation Premium

**Date :** 2026-08-02  
**Produit :** ComptaPilot  
**Owner données :** ComptaPilot (facturation fiscale — Blueprint ch. 07 / 08)

---

## Verdict

| Zone | État |
|------|------|
| Spec « Facturation Premium » dédiée | **Absente** (Blueprint : reprise après P0, non démarrée) |
| Page `/facturation` fonctionnelle | **Livrée** (CRUD docs, lignes, PDF, envoi, paiement, relances) |
| UI premium alignée Dashboard Premium | **Non démarrée** avant cette session |
| Branches / TODOs / mockups premium | **Aucun** trouvé sous ce nom |
| Moteurs / API billing métier | **Hors scope** P0.5 UI |

---

## Ce qui est déjà livré (produit)

| Capacité | Preuve |
|----------|--------|
| Overview facturation (`billingOverview`) | `api.billingOverview` → `BillingOverview` |
| Création / édition devis, factures, avoirs | `FacturationPage` + `SalesDocLinesEditor` |
| Lignes multi-articles + catalogue | Branché (commercial-readiness Vague 1) |
| Preview / PDF / envoi e-mail | `SalesDocPreviewModal` |
| Paiement (dont partiel) | `InvoicePaymentModal` |
| Actions : signer, convertir, relancer, avoir, dupliquer | `billingAction` / `createSalesDoc` |
| Prefill client / deep-link `?doc=` | Query params |
| Stats overview | `documents`, `customers`, `unpaid`, `unpaid_amount`, `quotes`, `invoices`, `credits` |
| Flag SMTP | `smtp_configured` (exposé, peu mis en avant UI) |

Docs connexes utiles : `commercial-readiness/` (envoi, preview), `salespilot-proposal-invoice-bridge-v1.md`, `billing-system-v2-certification-report.md` (SaaS entitlement — **≠** facturation client).

---

## Ce qui est incomplet / non démarré (premium)

| Élément | Note |
|---------|------|
| Spec layout premium facturation | Manquante avant P0.5 |
| Header premium (typo, meta, source) | Page-head générique |
| Hiérarchie KPI (impayés mis en avant) | Grille `.stats` plate |
| Sections / rythme type FCC | Formulaire + table sans hiérarchie visuelle forte |
| Empty states premium | `EmptyState` basique présent |
| Widget Framework | Non utilisé (pertinent surtout pour dashboards ; page opérationnelle) |
| Responsive polish dédié | Breakpoint 960px basique |

---

## Hors chantier (NO GO immédiat)

- S1.3 Relations / Party unifié
- Nouveau Pilot
- Modification Financial Engine / Accounting Engine
- Invention de métriques ou empty data fake
- Refonte API `/billing/*`

---

## Checklist Blueprint ch. 10 (P0.5 UI)

| Point | Réponse P0.5 |
|-------|----------------|
| Owner | ComptaPilot — lecture seule `billingOverview` + actions déjà existantes |
| Autonomie | Page autonome ComptaPilot ; pas de dépendance SalesPilot |
| Zero ressaisie | Aucune nouvelle saisie ; UI uniquement |
| Widgets | Non requis pour formulaire opérationnel ; KPI locaux OK |
| Aura | Non touché |
| Trois Lois | Respectées (pas d’absorption, pas de nouveau owner) |
| Zero verrou | Aucune donnée liée à un autre Pilot |

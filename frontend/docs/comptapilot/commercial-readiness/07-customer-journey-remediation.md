# 07 — Remediation parcours client (PHASE A1.1)

**Date :** 2026-08-01  
**Périmètre :** Client → Devis → Facture → Envoi → Paiement (ComptaPilot métier uniquement)  
**Source de vérité :** docs C1 / C1.1 — pas d’inventaire inventé hors parcours.

---

## Synthèse exécutive

| | |
|---|---|
| **P0 du parcours** | Déjà traités en C1.1 (lignes, catalogue, envoi SMTP/mailto) |
| **P1 corrigés** | P1-1, P1-7, P1-9, P1-10 |
| **Score parcours** | **Avant : 79 / 100** → **Après : 97 / 100** |
| **Cible** | ≥ 95 % |
| **Verdict** | **GO** pour ce parcours (sous réserve ops : essai activé + SMTP ou mailto accepté) |

---

## Étape 1 — Inventaire (parcours uniquement)

### P0 (déjà faits — C1.1)

| ID | Titre | Statut |
|---|---|---|
| P0-2 | Lignes devis/facture UI | ✅ |
| P0-3 | Envoi e-mail SMTP / mailto | ✅ |
| P0-6 | Catalogue branché aux lignes | ✅ |

*(P0-1 fournisseurs, P0-4 TVA, P0-5 clôture hors ce parcours — non retouchés.)*

### P1 (corrigés dans A1.1)

| ID | Titre | Correction |
|---|---|---|
| P1-1 | Dupliquer devis | Bouton Dupliquer (`DevisPage` + `FacturationPage`) via `createSalesDoc` + `buildDuplicateSalesDocPayload` |
| P1-7 | Paiement one-click | Modal montant / date / mode / référence (`InvoicePaymentModal`) ; BE `paid_at` optionnel |
| P1-9 | Copy mailto obsolète | Alignement `SettingsPage` + modal d’envoi (SMTP ou mailto, pas « toujours Gmail ») |
| P1-10 | Mentions légales / SIRET | Garde avant envoi + lien `/organisation` + ack temporaire |

### P1 hors parcours (non traités — STOP)

P1-2 OCR · P1-3 dépôt simulé · P1-4 banque · P1-5 validation compta · P1-6 rapprochement · P1-8 essai/Stripe (ops Vague 0) · P1-11 export · P1-12 vault · P1-13 CA3 · P1-14 verrou clôture.

### P2 sur le parcours (backlog, non bloquants score)

| ID | Titre |
|---|---|
| P2-2 | Confirm delete via `window.confirm` |
| P2-3 | Client libre (datalist) vs id |
| P2-4 | Signature devis opaque UX |
| P2-5 | Relance sans preview e-mail |

---

## Avant | Après

| Capacité | Avant A1.1 | Après A1.1 |
|---|---|---|
| Client CRUD | ✅ | ✅ |
| Devis multi-lignes + catalogue | ✅ | ✅ |
| Dupliquer devis | ❌ | ✅ |
| Convertir → facture | ✅ | ✅ |
| PDF | ✅ | ✅ |
| Envoi SMTP / mailto | ✅ (copy Settings obsolète) | ✅ copy alignée |
| Mentions légales avant envoi | ⚠ silencieux | ✅ alerte + ack |
| Paiement | ⚠ one-click solde | ✅ partiel (montant, date, réf.) |

---

## Score Commercial Readiness — parcours uniquement

Pondération indicative (100 pts) :

| Axe | Max | Avant | Après |
|---|---|---|---|
| Client | 15 | 15 | 15 |
| Devis (CRUD + lignes + dupliquer) | 25 | 18 | 25 |
| Facture / conversion | 15 | 15 | 15 |
| Envoi + PDF + mentions | 25 | 19 | 24 |
| Paiement | 20 | 12 | 18 |
| **Total** | **100** | **79** | **97** |

Écarts restants (−3) : mentions libres encore optionnelles (soft) ; paiement sans historique UI dédié / sans encaissement bancaire lié ; relance P2.

---

## Risques restants

1. **Mailto** : jointure PDF manuelle — support si mal compris.
2. **Org incomplète** : envoi possible avec ack — PDF peut manquer SIRET.
3. **Paiement** : enregistrement métier local, pas de rapprochement bancaire (hors parcours).
4. **Ops Vague 0** : essai Stripe / SMTP prod non validés ici (RUNTIME checklist A3/A4).

---

## Décision

| Question | Réponse |
|---|---|
| Parcours Client→…→Paiement commercialisable ? | **GO** (≥ 95 %) |
| GO produit global / fiscal / OCR / banque ? | **Non** — hors scope A1.1 |
| Prochaine vague ? | Autre parcours (OCR, banque…) **uniquement** sur demande — **STOP** ici |

---

## Validation

| Check | Résultat |
|---|---|
| vitest (duplicate, legal, lines, date paiement) | OK (8) |
| `npm run build` (tsc + vite) | OK |
| pytest `test_sales_billing.py` | OK (4) |

---

## Fichiers principaux

**FE :** `DevisPage.tsx`, `FacturationPage.tsx`, `SalesDocPreviewModal.tsx`, `InvoicePaymentModal.tsx`, `SettingsPage.tsx`, `salesDocDuplicate.ts`, `orgLegalCompleteness.ts`  
**BE :** `PaymentIn.paid_at`, `register_payment(..., paid_at=)`  
**Docs :** ce fichier + README / journey / matrix / checklist mis à jour

---

## STOP

PHASE A1.1 terminée. Ne pas démarrer OCR / banque / TVA profondeur / clôture dure.

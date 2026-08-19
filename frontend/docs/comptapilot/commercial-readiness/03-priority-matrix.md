# 03 — Matrice de priorités

Tous les écarts relevés pour ComptaPilot commercial.  
Effort : S ≤ 2 j · M 3–8 j · L > 8 j. Impact : 1 faible → 5 critique.  
**P0 mis à jour après C1.1.**

---

## P0 — Bloque lancement (statuts C1.1)

| ID | Problème | Impact | Effort | Route / fichier | Statut |
|---|---|---|---|---|---|
| P0-1 | CRUD fournisseurs | 5 | M | `/fournisseurs` | ✅ Traité |
| P0-2 | Lignes devis/facture UI | 5 | M | `/devis`, `/facturation` | ✅ Traité |
| P0-3 | Envoi e-mail si SMTP off | 5 | S–M | `SalesDocPreviewModal` | ✅ Mailto fallback |
| P0-4 | Déclaration TVA | 4 | L→MVP | `/tva` | ✅ MVP (pas CA3) |
| P0-5 | Clôture | 4 | L→MVP | `/cloture` | ✅ MVP (soft) |
| P0-6 | Catalogue non branché | 4 | M | `SalesDocLinesEditor` | ✅ Traité |

---

## P1 — Très important

| ID | Problème | Impact | Effort | Preuve | Statut |
|---|---|---|---|---|---|
| P1-1 | Dupliquer devis | 3 | S | Bouton Dupliquer FE | ✅ A1.1 |
| P1-2 | Flag OCR Trial/Starter false | 4 | S | `plan_registry` ; runtime | Ouvert |
| P1-3 | Steps dépôt simulés | 3 | S | `DepositPage` timers | Ouvert |
| P1-4 | Banque providers réels | 4 | M | `/banque` ; runtime | Ouvert |
| P1-5 | Entitlement validation compta | 3 | S | BE `ACCOUNTING_VALIDATION` | Ouvert |
| P1-6 | Pas de rapprochement manuel | 3 | M | Banking auto only | Ouvert |
| P1-7 | Paiement one-click | 3 | S | `InvoicePaymentModal` | ✅ A1.1 |
| P1-8 | Activation essai / Stripe | 5 | S–M | `trialOnboarding` ; runtime | Ouvert (ops) |
| P1-9 | Copy mailto obsolète | 2 | S | Settings + modal envoi | ✅ A1.1 |
| P1-10 | Mentions légales / SIRET incomplets | 3 | S | Garde `SalesDocPreviewModal` | ✅ A1.1 |
| P1-11 | Export comptable off Starter | 3 | — | Plan Professional | Ouvert |
| P1-12 | Vault archive PDF-only | 3 | M | `ResultPage.onArchive` | Ouvert |
| P1-13 | TVA CA3 / périodicité fiscale réelle | 4 | L | Suite de P0-4 MVP | Ouvert |
| P1-14 | Verrouillage clôture écritures | 4 | L | Suite de P0-5 MVP | Ouvert |

---

## P2 — Amélioration

| ID | Problème | Impact | Effort | Preuve |
|---|---|---|---|---|
| P2-1 | Créer 2ᵉ org désactivé | 2 | M | `OrganizationSwitcher` |
| P2-2 | Confirm delete via `window.confirm` | 2 | S | Devis/Facturation |
| P2-3 | Client libre (datalist) vs id | 2 | S | Facturation form |
| P2-4 | Signature devis opaque UX | 2 | S | Bouton sans e-sign |
| P2-5 | Relance sans preview e-mail | 2 | S | `billingAction` |
| P2-6 | Reports = hub de liens | 1 | S | `/reports` |
| P2-7 | Bridge document produit off | 2 | — | Doc bridge |
| P2-8 | Multi-user off Starter | 2 | — | Plan registry |
| P2-9 | Progress UI accounting / banking | 2 | S | États UI |

---

## P3 — Cosmétique

| ID | Problème | Impact | Effort |
|---|---|---|---|
| P3-1 | Labels statut devis en anglais | 1 | S |
| P3-2 | Densité boutons actions facturation | 1 | S |
| P3-3 | Placeholder onboarding banque = redirect | 1 | — |

---

## Synthèse comptage

| Priorité | Nb |
|---|---|
| P0 ouverts | 0 |
| P0 traités | 6 |
| P1 traités (parcours client A1.1) | 4 |
| P1 restants | 10 |
| P2 | 9 |
| P3 | 3 |

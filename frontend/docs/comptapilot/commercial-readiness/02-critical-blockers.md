# 02 — Bloqueurs critiques (P0 + P1 critiques)

Preuves uniquement code / docs existantes.  
**Statuts mis à jour après PHASE C1.1.**

---

## Verdict P0

Les 6 P0 documentés en C1 sont **traités en MVP** (parcours semaine démoable). Limites restantes documentées ci-dessous (TVA ≠ CA3 ; clôture ≠ verrou technique).

---

## P0 — Bloqueurs lancement

### P0-1 — Pas de gestion fournisseurs (CRUD) → ✅ Traité

| | |
|---|---|
| **Impact** | Impossible d’« ajouter un fournisseur » |
| **Correction C1.1** | Page `/fournisseurs` + `POST/PATCH/DELETE /contacts` + launch `action_path: /fournisseurs` |
| **FE** | `FournisseursPage.tsx`, nav Relations |
| **Effort** | M |

---

### P0-2 — Devis / factures sans lignes (UI) → ✅ Traité

| | |
|---|---|
| **Impact** | Document commercial non utilisable |
| **Correction C1.1** | `SalesDocLinesEditor` branché sur `lines` BE/PDF |
| **FE** | `DevisPage`, `FacturationPage`, `salesDocLines.ts` |
| **Effort** | M |

---

### P0-3 — Envoi facture / devis dépendant SMTP plateforme → ✅ Traité (fallback)

| | |
|---|---|
| **Impact** | Bouton désactivé si SMTP off |
| **Correction C1.1** | Si `can_send_direct` : envoi serveur ; sinon mailto + ack + PDF download ; statut BE `mailto_opened` (pas faux « sent » SMTP) |
| **FE** | `SalesDocPreviewModal.tsx` |
| **À valider runtime** | SMTP/Brevo prod pour envoi joint auto |
| **Effort** | S–M |

---

### P0-4 — Déclaration TVA absente → ✅ MVP

| | |
|---|---|
| **Impact** | Pas de parcours TVA |
| **Correction C1.1** | `/tva` : KPI engine + export CSV + marquage `vat_declaration` via `/fiscal/periods` |
| **Limite** | Pas de formulaire CA3 / dépôt DGFiP |
| **Effort** | L → MVP M |

---

### P0-5 — Clôture absente → ✅ MVP

| | |
|---|---|
| **Impact** | Promesse clôture non tenue |
| **Correction C1.1** | `/cloture` : checklist + marquage `period_close` |
| **Limite** | Pas de verrouillage des écritures / factures |
| **Effort** | L → MVP M |

---

### P0-6 — Catalogue non utilisable dans la facturation → ✅ Traité

| | |
|---|---|
| **Impact** | Double saisie |
| **Correction C1.1** | Sélecteur catalogue dans `SalesDocLinesEditor` |
| **Effort** | M (avec P0-2) |

---

## P1 critiques

### P1-1 — Dupliquer devis → ✅ Traité (A1.1)
### P1-2 — OCR / plan Starter *(hors parcours client)*
### P1-3 — Progression dépôt factice *(hors parcours)*
### P1-4 — Banque : providers & credentials *(hors parcours)*
### P1-5 — Validation comptable gated *(hors parcours)*
### P1-6 — Rapprochement bancaire manuel absent *(hors parcours)*
### P1-7 — Paiement facture trop rudimentaire → ✅ Traité (A1.1 — modal partiel)
### P1-8 — Essai & verrouillage nav *(ops Vague 0 / runtime)*
### P1-9 — Copy mailto → ✅ Traité (A1.1)
### P1-10 — Mentions légales / SIRET → ✅ Traité (A1.1 — garde envoi)

Détail : `07-customer-journey-remediation.md`.

---

## Compteurs

| Classe | Nombre |
|---|---|
| P0 ouverts | **0** |
| P0 traités MVP | **6** |
| P1 parcours client traités | **4** (P1-1, P1-7, P1-9, P1-10) |
| P1 critiques hors parcours restants | **6** (OCR, dépôt, banque×2, compta, essai) |

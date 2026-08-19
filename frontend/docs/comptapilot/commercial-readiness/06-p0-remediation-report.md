# 06 — Rapport de remediation P0 (PHASE C1.1)

**Date :** 2026-08-01  
**Périmètre :** ComptaPilot frontend (+ backend minimal contacts / fiscal)  
**Contrainte :** uniquement les 6 P0 de l’audit C1 — pas de P1, pas SalesPilot / Home / Launcher / Command Center / IA.

---

## Synthèse exécutive

| | |
|---|---|
| **P0 corrigés (MVP)** | P0-1, P0-2, P0-3, P0-4, P0-5, P0-6 |
| **P0 restants ouverts** | **Aucun** |
| **Score commercial estimé** | **Avant : 28 / 100** → **Après : 68 / 100** |
| **Verdict** | **GO conditionnel** essai 7 j (SMTP ou mailto ; TVA/clôture = MVP) |

---

## Backlog P0 (détail)

| ID | Titre | Cause | Impact client | Correction | Temps estimé | Risques | Dépendances | Statut |
|---|---|---|---|---|---|---|---|---|
| P0-1 | Fournisseurs absents | Pas de route FE ; pas de POST `/contacts` | Impossible d’onboarder achats | Page `/fournisseurs` + CRUD contacts + launch path | M (~1–2 j) | Soft-delete archive only | Contacts BE | ✅ |
| P0-2 | Factures/devis sans lignes | UI n’envoyait pas `lines` | PDF / devis non commerciaux | `SalesDocLinesEditor` + API `lines` | M (~1–2 j) | Montant HT recalculé côté FE | BE `lines_json` déjà prêt | ✅ |
| P0-3 | Envoi e-mail SMTP | Bouton disabled si `!can_send_direct` | Impossible de livrer la facture | Fallback mailto + ack ; statut `mailto_opened` | S–M (~0,5–1 j) | Mailto ≠ envoi confirmé | BE `send_mode=mailto` | ✅ |
| P0-4 | TVA déclarative | KPI seul, pas d’écran | Dirigeant sans parcours TVA | `/tva` KPI + CSV + marquage fiscal | MVP M (plein L) | Pas de CA3 / filtre mois strict KPI | Financial Engine + `/fiscal/periods` | ✅ MVP |
| P0-5 | Clôture manquante | Zéro route/API | Promesse marketing non tenue | `/cloture` checklist + marqueur | MVP M (plein L) | Pas de verrou écritures | `/fiscal/periods` | ✅ MVP |
| P0-6 | Catalogue non branché | CRUD isolé | Double saisie | Sélecteur catalogue dans lignes | Inclus P0-2 | Catalogue vide = saisie libre | `/billing/catalog` | ✅ |

---

## P0 corrigés — détails techniques

### P0-2 + P0-6 — Lignes + catalogue

- Composant `SalesDocLinesEditor` + helpers `salesDocLines.ts`
- Branché dans `DevisPage` et `FacturationPage`
- Payload `lines: [{ label, quantity, unit_price, catalog_item_id }]`
- Tests : `salesDocLines.test.ts`

### P0-3 — E-mail

- `SalesDocPreviewModal` : serveur si `can_send_direct`, sinon téléchargement PDF + mailto + case à cocher
- BE : statut `mailto_opened` (ne simule plus un `sent` SMTP)

### P0-1 — Fournisseurs

- BE : `create_manual_contact`, `POST /contacts`, `DELETE` (archive)
- FE : `FournisseursPage`, nav, route `/fournisseurs`
- Launch dashboard : `action_path: /fournisseurs`
- Tests : `test_contact_manual_create.py`

### P0-4 / P0-5 — TVA & clôture MVP

- BE : table `fiscal_period_records`, router `/api/fiscal/periods`
- FE : `/tva`, `/cloture` + nav Pilotage
- Tests : `test_fiscal_period_model.py`

---

## P0 restants

Aucun P0 **ouvert** au sens audit. **Limites MVP** à traiter en P1/Vague 4 :

| Sujet | Raison |
|---|---|
| CA3 / dépôt fiscal | Produit fiscal complet hors sprint P0 |
| Verrouillage écritures à la clôture | Nécessite modèle comptable de périodes |
| Envoi serveur sans SMTP | Ops / config runtime (mailto = filet) |

---

## Nouveaux risques

1. **Mailto** : l’utilisateur doit joindre le PDF manuellement — risque support si mal compris.
2. **TVA KPI** : solde engine global, pas forcément filtré strictement sur le mois UI sélectionné.
3. **Clôture soft** : un utilisateur peut encore éditer des docs après marquage — à clarifier dans le pitch.
4. **POST contacts** : doublons durs SIRET/TVA gérés ; doublons soft possibles.

---

## Commercial Readiness Score

| Axe (pondération indicative) | Avant | Après |
|---|---|---|
| Parcours ventes (clients → devis → facture → PDF → envoi) | 12/25 | 23/25 |
| Achats / fournisseurs | 2/15 | 13/15 |
| Documents / OCR | 8/15 | 8/15 (inchangé P1) |
| Fiscalité (TVA / clôture) | 2/20 | 12/20 |
| Ops / config (SMTP, essai, banque) | 4/15 | 7/15 |
| **Total** | **28** | **68** |

---

## Notes de validation

| Check | Résultat |
|---|---|
| `vitest` `salesDocLines.test.ts` | OK |
| `npm run build` (tsc + vite) | OK |
| `pytest` contacts manuels + fiscal model + contact creation | OK (8 passed) |
| Régression navModel `/abonnement` → parametres | Échec **préexistant** (hors P0) |

---

## Fichiers principaux touchés

**Frontend :** `SalesDocLinesEditor.tsx`, `salesDocLines.ts`, `DevisPage.tsx`, `FacturationPage.tsx`, `SalesDocPreviewModal.tsx`, `FournisseursPage.tsx`, `VatDeclarationPage.tsx`, `PeriodClosePage.tsx`, `api.ts`, `App.tsx`, `navModel.ts`, `NavIcons.tsx`, `resolveRuntimeProductFromPath.ts`

**Backend :** `contacts` router + `creation_service`, `sales_email.py`, `dashboard_launch/service.py`, `models_fiscal.py`, `routers/fiscal.py`, `main.py`, `database.py`

**Docs :** ce dossier `commercial-readiness/*`

---

## STOP

PHASE C1.1 terminée. Ne pas démarrer C1.2 / P1 dans ce livrable.

# ComptaPilot — Audit de maturité commerciale (PHASE C1 → C1.1 → A1.1)



**Date audit :** 2026-08-01  

**Date remediation P0 :** 2026-08-01 (PHASE C1.1)  

**Date remediation parcours client :** 2026-08-01 (PHASE A1.1)  

**Périmètre :** UI + clients API frontend (routes Compta) ; backend minimal uniquement si API absente (contacts POST, fiscal periods, paiement `paid_at`).



---



## Verdict



| Indicateur | Valeur |

|---|---|

| Verdict global produit | **GO conditionnel** (hors fiscal CA3 / banque / OCR) |

| Parcours Client→Devis→Facture→Envoi→Paiement | **GO** (score **97 / 100**) — voir `07-customer-journey-remediation.md` |

| P0 (bloqueurs) | **0 ouverts** · **6 traités en MVP** |

| P1 parcours client | **4 traités** (P1-1, P1-7, P1-9, P1-10) |

| Score commercial global (estimé) | **Avant C1 ~28 → après C1.1 ~68** |

| Score **parcours client** | **Avant A1.1 79 → Après 97** |



---



## Méthode



1. Cartographier les routes Compta dans `frontend/src/App.tsx`.

2. Pour chaque étape du parcours : page / formulaire / action → appel `api.*` ou service dédié → endpoint backend (si besoin).

3. Distinguer :

   - **Implémenté UI + branché API**

   - **UI présente, dépendance config / entitlement**

   - **Placeholder / copy obsolète / non branché**

4. Ne pas inventer de bloqueur sans pointeur fichier/route. Sinon : **À valider runtime**.



Sources principales : `ClientsPage`, `FournisseursPage`, `DevisPage`, `FacturationPage`, `SalesDocPreviewModal`, `InvoicePaymentModal`, `VatDeclarationPage`, `PeriodClosePage`, `DepositPage`, `api.ts`, launch dashboard.



---



## Comment lire



| Fichier | Contenu |

|---|---|

| `01-user-journey.md` | Parcours étape par étape ✅ / ⚠ / ❌ |

| `02-critical-blockers.md` | P0 (+ P1 critiques) avec preuves / statut remediation |

| `03-priority-matrix.md` | Tous les écarts P0–P3, effort, impact |

| `04-launch-checklist.md` | Go / No-go essai 7 jours |

| `05-recommendations.md` | Ordre recommandé |

| `06-p0-remediation-report.md` | Livrable C1.1 — P0 |

| `07-customer-journey-remediation.md` | **Livrable A1.1** — parcours client |



Légende statut :



- ✅ fonctionne (UI + API, usage client plausible)

- ⚠ amélioration UX / config / limite métier

- ❌ bloquant pour le parcours annoncé



---



## Synthèse parcours (aperçu)



| Zone | État |

|---|---|

| Organisation / inscription | ✅ (register) ; ⚠ 2ᵉ org désactivée |

| Client | ✅ CRUD `/clients` |

| Fournisseur | ✅ CRUD `/fournisseurs` (+ POST `/contacts`) |

| Devis / facture CRUD + convert / payer | ✅ lignes + catalogue + **dupliquer** + **paiement partiel** |

| Dupliquer devis | ✅ |

| Envoyer facture | ✅ SMTP si config ; ⚠ mailto fallback ; **garde mentions légales** |

| PDF | ✅ (tableau lignes si `lines_json`) |

| Archiver | ✅ Vault |

| Recherche | ✅ `/search` |

| Import + OCR + validation doc | ✅ `/deposit` → `/result/:id` |

| Écriture comptable | ✅ propositions + validate ; pas d’auto-posting |

| Banque | ✅ UI Banking Engine ; providers **à valider runtime** |

| TVA | ✅ MVP `/tva` — pas CA3 auto |

| Clôture | ✅ MVP `/cloture` — pas de verrou écritures |



Détail : `01-user-journey.md`. Rapport parcours : `07-customer-journey-remediation.md`.



---



## Backlog P0 (résumé)



| ID | Titre | Statut C1.1 |

|---|---|---|

| P0-1 | Fournisseurs CRUD | ✅ |

| P0-2 | Lignes devis/facture | ✅ |

| P0-3 | Envoi e-mail / SMTP | ✅ (fallback mailto) |

| P0-4 | TVA déclarative | ✅ MVP |

| P0-5 | Clôture | ✅ MVP |

| P0-6 | Catalogue branché | ✅ |



---



## Fichiers



```

frontend/docs/comptapilot/commercial-readiness/

├── README.md

├── 01-user-journey.md

├── 02-critical-blockers.md

├── 03-priority-matrix.md

├── 04-launch-checklist.md

├── 05-recommendations.md

├── 06-p0-remediation-report.md

└── 07-customer-journey-remediation.md

```



**STOP PHASE A1.1** — pas d’autre parcours (OCR, banque…) dans ce sprint.



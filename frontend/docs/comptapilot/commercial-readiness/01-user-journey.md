# 01 — Parcours utilisateur (semaine type)



Chaque étape : statut, gravité, impact client, effort estimé, priorité.  

Preuves = routes / fichiers FE (et BE si nécessaire).  

**Mis à jour après C1.1 (P0) et A1.1 (parcours client).**



---



## Tableau parcours



| # | Étape | Statut | Gravité | Impact client | Effort | Priorité | Preuve |

|---|---|---|---|---|---|---|---|

| 1 | Créer organisation | ✅ | — | Inscription crée org | — | — | `/register` → `RegisterPage` + `api.register` ; onboarding `/onboarding/entreprise/*` |

| 1b | 2ᵉ organisation | ⚠ | Faible | Bouton crée org désactivé | S | P2 | `OrganizationSwitcher` : `disabled` « Bientôt disponible » |

| 2 | Client | ✅ | — | CRUD + empty states | — | — | `/clients` → `ClientsPage` → `/billing/customers` |

| 3 | Fournisseur | ✅ | — | CRUD fournisseurs | M | P0 traité | `/fournisseurs` → `FournisseursPage` → `POST/GET/PATCH/DELETE /contacts` ; launch `action_path: /fournisseurs` |

| 4 | Devis (créer) | ✅ | — | Création **avec lignes** (+ catalogue) | M | P0 traité | `/devis` ; `createSalesDoc` + `lines` ; `SalesDocLinesEditor` |

| 5 | Modifier / supprimer devis | ✅ | — | Edit + delete confirmés | — | — | `DevisPage` / `FacturationPage` → `updateSalesDoc` / `deleteSalesDoc` |

| 6 | Dupliquer devis | ✅ | — | Copie brouillon + édition | S | P1 traité A1.1 | Bouton Dupliquer ; `buildDuplicateSalesDocPayload` |

| 7 | Transformer en facture | ✅ | — | Convert OK (lignes reprises BE) | — | — | `act(doc,'convert')` → `POST /billing/documents/{id}/convert` |

| 8 | Envoyer facture | ✅/⚠ | — | SMTP si config ; sinon mailto + ack ; **garde mentions légales** | M | P0+P1 traités | `SalesDocPreviewModal` ; `orgLegalCompleteness` |

| 9 | PDF | ✅ | — | Aperçu + téléchargement + lignes | — | — | `openSalesDocPdfBlob` / `downloadSalesDocPdf` → `/billing/documents/{id}/pdf` |

| 10 | Archiver | ✅ | — | Vault à l’envoi serveur + `/documents` | — | — | `emailSalesDoc` archive ; `archiveVaultDocument` |

| 11 | Rechercher | ✅ | — | Recherche multi-types | — | — | `/search` → `api.searchElfis` |

| 12 | Importer document | ✅ | — | Dropzone PDF/images | — | — | `/deposit` → `api.uploadDocument` |

| 13 | OCR / extraction | ⚠ | Haute | Pipeline branché ; étapes UI simulées ; flag plan | S–M | P1 | `DepositPage` timers ; `plan_registry` |

| 14 | Validation document | ✅ | — | Édition champs + reprocess | — | — | `/result/:id` |

| 15 | Écriture comptable | ⚠ | Haute | Propositions + validate humaine | M | P1 | `/accounting/*` |

| 16 | Paiement (facture) | ✅ | — | Modal montant / date / mode / référence | S | P1 traité A1.1 | `InvoicePaymentModal` → `POST .../pay` |

| 17 | Banque | ⚠ | Haute | UI Banking Engine ; providers runtime | — | P1 | `/banque` |

| 18 | TVA | ✅/⚠ | — | Écran période + export + marquage ; **pas CA3 auto** | L→M | P0 traité MVP | `/tva` → `VatDeclarationPage` + KPI finance + `/fiscal/periods` |

| 19 | Clôture | ✅/⚠ | — | Checklist + marqueur ; **pas de verrou écritures** | L→M | P0 traité MVP | `/cloture` → `PeriodClosePage` + `/fiscal/periods` |



---



## Enchaînement critique (happy path minimal)



```

/register → /abonnement|essai → /onboarding/entreprise → /dashboard

  → /clients → /fournisseurs

  → /catalogue (opt.) → /devis|/facturation (lignes) → dupliquer (opt.) → convert → PDF

  → envoi e-mail (SMTP ou mailto, mentions OK) → payer (partiel OK)

  → /deposit → /result/:id → /accounting/proposals/:id (validate)

  → /banque (si provider) → /tva → /cloture → /finance

```



**Ruptures restantes (hors parcours client A1.1) :** OCR timers, banque providers, CA3 auto, verrouillage fiscal dur.



---



## Notes transverses



| Sujet | Constat |

|---|---|

| Catalogue | ✅ CRUD `/catalogue` **branché** aux lignes devis/facture |

| Mentions légales org | ✅ `/organisation` + garde envoi PDF |

| Permissions nav | Filtrage `navModel` + trial lock |

| Empty states | Présents clients / fournisseurs / facturation / accounting / search |



---



## Légende effort



- **S** ≤ 2 j · **M** 3–8 j · **L** > 8 j



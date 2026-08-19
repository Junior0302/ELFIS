# Certification — Banking Platform V1

Date : 26/07/2026
Périmètre : Banking Engine, Connector Layer, Sync Engine, API `/banking/*`,
frontend `/banque`, Cockpit Admin `/elfadmin/banque`.

## Critères de certification

### ✔ Fournisseur interchangeable

- Interface commune `BankConnector` (`connect`, `disconnect`, `refresh`,
  `list_accounts`, `list_transactions`, `health`) dans
  `backend/app/banking/connectors/base.py`.
- Trois implémentations : `demo` (hors ligne), `bridge`, `powens`.
- Le code métier n'importe aucun connecteur : résolution exclusivement via
  `connectors/registry.py`. Les tests injectent un connecteur `fake` sans
  modifier engine/sync/API — preuve d'interchangeabilité.

### ✔ Banking Engine source de vérité

- `backend/app/banking/engine.py` centralise banques connectées, comptes,
  IBAN, devises, soldes, synchronisations et historique.
- Tables uniques : `bank_accounts` / `bank_transactions` (réutilisées et
  enrichies), `elfis_bank_connections`, `elfis_bank_sync_runs`.
- L'import CSV historique alimente la même source de vérité (`source="csv"`).

### ✔ Transactions normalisées

- Modèle unique `NormalizedTransaction` : id externe, date, libellé, montant,
  devise, compte, catégorie, statut, source — quel que soit le fournisseur.
- Dates stockées en ISO, catégorisation automatique réutilisant les règles
  existantes (`services/banking.categorize`).

### ✔ Synchronisation fiable

- Première importation + synchronisation incrémentale (curseur par connexion).
- Détection des doublons : `external_id` + empreinte (montant, libellé, date).
- Retry automatique (erreurs transitoires, `max_attempts` configurable).
- Reprise après erreur : curseur persisté après chaque compte,
  `resumed_from_cursor` tracé dans le journal.
- Journalisation complète (`elfis_bank_sync_runs`) + événements
  `banking.sync.completed.v1` / `banking.sync.failed.v1`.

### ✔ APIs cohérentes

- `GET /banking/connectors`, `POST /banking/connectors/connect`,
  `POST /banking/connectors/{id}/disconnect`, `GET /banking/accounts`,
  `GET /banking/transactions`, `POST|GET /banking/sync`,
  `GET /banking/status`, `GET /banking/health`,
  `GET /platform/banking/overview` (admin).
- Permissions existantes réutilisées : `bank.read`, `bank.connect` ;
  abonnement actif requis ; isolation multi-organisation testée.

### ✔ Frontend fonctionnel

- Page `/banque` (`src/pages/BankingPage.tsx`) : onglets **Banques**,
  **Comptes**, **Transactions**, **Synchronisation**, **État des connexions**.
- Client API typé `src/services/bankingApi.ts` (+ tests vitest).
- Entrée de navigation « Banque » (permission `bank.read`), module « Banque »
  visible dans le catalogue produit.
- Cockpit Admin `/elfadmin/banque` : connexions actives, erreurs,
  synchronisations, temps moyen, taux d'échec.
- `npx tsc --noEmit` : aucun diagnostic.

### ✔ Tests verts

Backend (`backend/tests/banking`, 31 tests) :

- connexion / déconnexion (+ idempotence, isolation org, événements)
- import initial, resynchronisation, synchronisation incrémentale
- doublons (external_id et empreinte)
- retry (transitoire récupéré, non-retryable immédiat, épuisement)
- reprise après erreur via curseur
- normalisation (modèle, validation, dates ISO, catégories, source)
- endpoints API complets, statut, santé, vue plateforme

```
31 passed (tests/banking)
```

Frontend (vitest) :

```
17 fichiers / 58 tests passed (dont bankingApi.test.ts)
```

Note : des échecs préexistants et indépendants existent dans
`backend/tests/events` lorsqu'ils sont exécutés en combinaison avec d'autres
suites (pollution de metadata `document_intake`/`migration_center` issue de
travaux antérieurs non commités). Vérifié : sur HEAD + changements Banking
uniquement, `tests/events` + `tests/banking` = 47/47 verts.

### ✔ Documentation créée

- `docs/banking/banking-platform-v1.md` (architecture, connecteurs, API,
  événements, observabilité, configuration).
- `frontend/docs/banking-platform-v1-certification.md` (ce document).

## Verdict

**BANKING PLATFORM V1 CERTIFIED**

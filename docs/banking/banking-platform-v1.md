# Banking Platform V1

Plateforme bancaire ELFIS Core indépendante des fournisseurs.

## Objectif

Aucun code métier ne dépend directement d'un fournisseur (Bridge, Powens…).
Tous les fournisseurs passent par la **Banking Integration Layer** (interface
`BankConnector`). Le **Banking Engine** est l'unique source de vérité des
comptes bancaires, transactions, soldes et synchronisations.

## Architecture

```
backend/app/banking/
├── banking_types.py      # Modèles normalisés (NormalizedAccount, NormalizedTransaction…)
├── banking_models.py     # ElfisBankConnection, ElfisBankSyncRun (journal)
├── banking_events.py     # Publication des événements banking.* sur l'Event Bus
├── engine.py             # Banking Engine — source de vérité
├── sync_engine.py        # Sync Engine — initial, incrémental, doublons, retry, reprise
├── health.py             # Santé connexions + fournisseurs + métriques
├── api/routes.py         # Endpoints /banking/* et /platform/banking/*
└── connectors/
    ├── base.py           # Interface commune BankConnector + ConnectorError
    ├── registry.py       # Registre des fournisseurs (point d'entrée unique)
    ├── demo.py           # Connecteur démo (hors ligne, déterministe)
    ├── bridge.py         # Connecteur Bridge (bridgeapi.io)
    └── powens.py         # Connecteur Powens
```

Les comptes et transactions restent stockés dans les tables existantes
`bank_accounts` / `bank_transactions` (réutilisation de l'existant), enrichies :

- `bank_accounts` : `connection_id`, `provider`, `external_id`
- `bank_transactions` : `status` (booked|pending), `source` (demo|bridge|powens|csv|manual)

L'import CSV historique (`/modules/banque/import-csv`) continue de fonctionner et
alimente la même source de vérité avec `source="csv"`.

## Connector Layer

Chaque fournisseur implémente l'interface commune :

```python
class BankConnector(ABC):
    def connect(*, organization_id, bank_name, options) -> str   # id connexion fournisseur
    def disconnect(provider_connection_id) -> None
    def refresh(provider_connection_id) -> None
    def list_accounts(provider_connection_id) -> list[NormalizedAccount]
    def list_transactions(provider_connection_id, account_external_id, *, since) -> list[NormalizedTransaction]
    def health() -> ConnectorHealth
```

Règles :

- Le code métier ne référence **jamais** un connecteur : il passe par
  `connectors.registry.get_connector(provider)`.
- `ConnectorError(retryable=True)` déclenche le retry automatique du Sync Engine.
- Un fournisseur sans identifiants se déclare `not_configured` et refuse `connect()`.
- Ajouter un fournisseur = implémenter l'interface + `register_connector(...)`.
  Rien d'autre ne change (engine, sync, API, frontend inchangés).

### Configuration des fournisseurs

| Variable | Rôle |
|----------|------|
| `BANKING_BRIDGE_API_URL` | URL API Bridge (défaut `https://api.bridgeapi.io`) |
| `BANKING_BRIDGE_CLIENT_ID` / `BANKING_BRIDGE_CLIENT_SECRET` | Identifiants Bridge |
| `BANKING_POWENS_API_URL` | URL API Powens (domaine dédié) |
| `BANKING_POWENS_CLIENT_ID` / `BANKING_POWENS_CLIENT_SECRET` | Identifiants Powens |
| `BANKING_SYNC_MAX_ATTEMPTS` | Tentatives max par sync (défaut 3) |

Le connecteur `demo` est toujours disponible (local, hors ligne, déterministe).

## Modèle de transaction normalisé

Toutes les transactions utilisent ce modèle, quel que soit le fournisseur :

| Champ | Description |
|-------|-------------|
| `external_id` | Identifiant externe (dédoublonnage) |
| `booked_at` | Date (stockée ISO `YYYY-MM-DD`) |
| `label` | Libellé |
| `amount` | Montant (+ crédit / − débit) |
| `currency` | Devise |
| `account_external_id` | Compte |
| `category` | Catégorie (auto via `services.banking.categorize` si absente) |
| `status` | `booked` ou `pending` |
| `source` | Fournisseur d'origine |

## Sync Engine

- **Première importation** : `sync_type=initial` (aucun run complété auparavant).
- **Incrémentale** : `since` = curseur (dernière date traitée avec succès).
- **Doublons** : par `external_id` (même compte) + empreinte
  `(montant, libellé, date)` pour les ids fournisseurs instables.
- **Retry** : erreurs `retryable` rejouées jusqu'à `max_attempts` ;
  erreurs non-retryables échouent immédiatement.
- **Reprise après erreur** : le curseur est persisté **après chaque compte**
  dans le journal ; le run suivant repart du curseur (`resumed_from_cursor=True`).
- **Journalisation** : chaque run est un `ElfisBankSyncRun` (statut, compteurs,
  tentatives, curseur, erreur, durée, correlation_id).

## Événements (Dashboard & Assistant IA)

Convention plateforme `module.entity.action.vN` :

| Événement métier | Nom sur le bus |
|------------------|----------------|
| transaction_created | `banking.transaction.created.v1` |
| transaction_updated | `banking.transaction.updated.v1` |
| sync_completed | `banking.sync.completed.v1` |
| sync_failed | `banking.sync.failed.v1` |
| connexion établie | `banking.connection.connected.v1` |
| connexion coupée | `banking.connection.disconnected.v1` |

Les payloads ne contiennent jamais d'IBAN ni de secret (règle `DomainEvent`).

## API

Prefixe `/api`, abonnement actif requis, permissions `bank.read` / `bank.connect` :

| Méthode | Endpoint | Rôle |
|---------|----------|------|
| GET | `/banking/connectors` | Fournisseurs disponibles + connexions de l'org |
| POST | `/banking/connectors/connect` | Connecter une banque `{provider, bank_name}` |
| POST | `/banking/connectors/{id}/disconnect` | Déconnecter |
| GET | `/banking/accounts` | Comptes (source de vérité) |
| GET | `/banking/transactions` | Transactions normalisées (`account_id`, `category`, `status`, `source`, `q`, pagination) |
| POST | `/banking/sync` | Déclencher une synchronisation (`connection_id` optionnel) |
| GET | `/banking/sync` | Journal des synchronisations |
| GET | `/banking/status` | Statut global (connexions, comptes, soldes, dernière/prochaine sync) |
| GET | `/banking/health` | Santé connexions + fournisseurs + métriques |
| GET | `/platform/banking/overview` | Cockpit Admin (platform admin uniquement) |

## Frontend

- `/banque` (`BankingPage.tsx`) — onglets : Banques, Comptes, Transactions,
  Synchronisation, État des connexions. Client API : `services/bankingApi.ts`.
- `/elfadmin/banque` (`PlatformBankingPage.tsx`) — Cockpit Admin : connexions
  actives, erreurs, synchronisations, temps moyen, taux d'échec.

## Observabilité

- **Logs** : logs structurés `banking_sync_started/completed/failed`,
  `banking_connection_connected/disconnected` avec `correlation_id`.
- **Metrics** : taux d'échec, durée moyenne, compteurs par run
  (`/banking/health`, `/platform/banking/overview`).
- **Tracing** : `correlation_id` par run, propagé dans tous les événements.
- **Audit** : journal `elfis_bank_sync_runs` persistant + événements durables
  sur l'Event Bus (`elfis_events`).

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/banking -q
cd ..\frontend
npm test
```

Couverture : connexion, déconnexion, import initial, resync, doublons
(external_id + empreinte), retry, reprise après erreur, normalisation,
endpoints API, santé, isolation multi-org.

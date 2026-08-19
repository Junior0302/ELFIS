# AI Financial Assistant V1 — ELFIS Core

## Objectif

Un assistant financier intelligent. Le LLM **n'est jamais** la source de vérité.
Toutes les données proviennent des moteurs internes (Financial, Banking, Vault…).
Le rôle du LLM se limite à : expliquer, résumer, conseiller, répondre.
Aucune réponse ne doit inventer de données.

## Architecture

```
backend/app/ai_assistant/
├── decision_engine.py      # Orchestrateur unique
├── context_builder.py      # Contexte borné (coûts)
├── tools.py                # Outils IA → moteurs
├── response_formatter.py   # 4 sections + explainability
├── memory.py               # Mémoire conversationnelle
├── feedback.py             # Utile / Inutile / Incorrect
├── observability.py        # Latence, tokens, coût, cache
├── events.py               # Bus événements
├── models.py               # Messages, feedback, préférences, runs
└── types.py                # StructuredAnswer, ToolResult…
```

Le chat (`POST /api/ai/chat`) ne dialogue **jamais** directement avec les moteurs :
`DecisionEngine` → intent → outils → formatage déterministe → (LLM optionnel) → validation.

## Decision Engine

Flux :

1. Construction du contexte (`ContextBuilder`)
2. Détection d'intention (routing déterministe)
3. Appel des outils internes uniquement
4. `format_deterministic` → faits / estimations / recommandations / manques
5. Enrichissement LLM optionnel (résumé + reco textuelles) avec garde anti-hallucination
6. Persistance mémoire + run d'observabilité + événements

## Context Builder

Rassemble automatiquement (borné pour optimiser les coûts) :

- KPIs (9 max)
- alertes (5 max)
- activité récente (5 max)
- synchronisations
- documents à traiter
- organisation
- préférences utilisateur
- historique récent (4 tours)

Limite soft : `MAX_CONTEXT_CHARS = 6000`.

## Réponses structurées

Chaque réponse contient **quatre sections** :

1. **Faits vérifiés** — chiffres issus des outils
2. **Estimations** — projections / alertes interprétées
3. **Recommandations** — avec explainability
4. **Informations manquantes** — ce qui manque pour trancher

## Explainability

Chaque recommandation expose :

- Pourquoi ?
- Quelles données ?
- Quel calcul ?
- Niveau de confiance (`high` / `medium` / `low`)
- Date des données (`data_as_of`)

## Outils IA

| Outil | Source |
|-------|--------|
| `get_cashflow` | Financial Engine |
| `get_unpaid_invoices` | Financial Engine + SalesDocument |
| `get_vat` | Financial Engine |
| `get_expenses` | Financial Engine |
| `get_documents` | Financial Engine (activité documents) |
| `search_transactions` | Banking Engine |
| `get_kpis` | Financial Engine |
| `get_alerts` | Financial alerts |
| `get_health_score` | Financial health |
| `get_sync_status` | Financial sync state |

Le LLM n'appelle **que** ces outils (via le Decision Engine).

## Mémoire

- `elfis_assistant_messages` : tours structurés (JSON)
- `elfis_assistant_preferences` : tone / language / focus (pas de secrets)
- Compatibilité `ai_conversations` (historique legacy)

## API

| Endpoint | Rôle |
|----------|------|
| `POST /api/ai/chat` | Conversation (`stream=true` → SSE) |
| `GET /api/ai/context` | Contexte construit |
| `GET /api/ai/tools` | Catalogue des outils |
| `GET /api/ai/history` | Historique structuré |
| `POST /api/ai/feedback` | useful / useless / incorrect |

## Frontend

Page `/copilote` (`CopilotePage.tsx`) :

- Conversation structurée (4 sections)
- Sources utilisées + outils + niveau de confiance
- Actions proposées (confirmation si modification)
- Feedback Utile / Inutile / Incorrect
- Historique latéral + suggestions

Client : `frontend/src/services/aiAssistantApi.ts`

## Actions proposées

- Voir les factures concernées → `/facturation`
- Ouvrir une transaction → `/banque`
- Créer un rappel → confirmation requise
- Afficher le Dashboard → `/finance`
- Préparer un rapport → confirmation requise

## Feedback

`POST /api/ai/feedback` avec `kind ∈ {useful, useless, incorrect}` + commentaire optionnel.
Événement : `ai.assistant.feedback.recorded.v1`.

## Observabilité

Table `elfis_assistant_runs` : latence totale, latence LLM, tokens, coût estimé,
outils appelés, cache hit, erreur.

Événement : `ai.assistant.chat.completed.v1`.

## Performance

- Cache intelligent TTL (`ai_assistant_cache_ttl_seconds`, défaut 45 s) clé = org + question + fingerprint données
- Streaming SSE (`stream=true`)
- Routing d'intention déterministe → limite les appels LLM
- Fallback 100 % déterministe si OpenAI absent / en erreur

## Anti-hallucination

- Les faits chiffrés sont produits **uniquement** par `format_deterministic`
- `merge_llm_enrichment` refuse un résumé LLM contenant un montant absent des faits
- Les recommandations LLM sont marquées confiance `low` et « aucun nouveau calcul »

## Tests

`backend/tests/ai_assistant/` — outils, contexte, formatage, Decision Engine, API, cache, mémoire, streaming.
Frontend : `aiAssistantApi.test.ts`.

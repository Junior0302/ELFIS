# Certification — AI Financial Assistant V1

Sprint : AI Financial Assistant V1 pour ELFIS Core.
Référence : `docs/ai/ai-financial-assistant-v1.md`.

## Critères de certification

### ✔ Decision Engine unique

- `backend/app/ai_assistant/decision_engine.py` est le seul orchestrateur conversationnel.
- `POST /api/ai/chat` et `finance_agent.answer_finance_question` délèguent au Decision Engine.
- Le chat ne dialogue jamais directement avec Financial / Banking / Vault.
- Vérifié par `tests/ai_assistant/test_decision_engine.py` et `test_api.py`.

### ✔ Outils IA utilisés

- 10 outils internes (`get_cashflow`, `get_unpaid_invoices`, `get_vat`, `get_expenses`,
  `get_documents`, `search_transactions`, `get_kpis`, `get_alerts`, `get_health_score`,
  `get_sync_status`) — catalogue exposé via `GET /api/ai/tools`.
- Routing d'intention déterministe (`detect_intent` + `INTENT_TOOLS`).
- Vérifié par `test_tools.py` (tous les outils appelables, outil inconnu rejeté).

### ✔ Réponses explicables

- Chaque recommandation porte un `Explanation` : pourquoi, données, calcul, confiance, date.
- Affiché dans le frontend (`StructuredBubble`).
- Vérifié par `test_context_and_format.py::test_recommendations_are_explainable`.

### ✔ Séparation faits / estimations / recommandations

- `StructuredAnswer` impose les 4 sections : `facts`, `estimates`, `recommendations`, `missing`.
- Formatage déterministe avant tout enrichissement LLM.
- Garde anti-hallucination : montants inventés dans le résumé LLM rejetés
  (`test_llm_cannot_inject_invented_amounts_in_summary`).

### ✔ Frontend fonctionnel

- `CopilotePage` : conversation, sources, confiance, actions, historique, feedback.
- Client typé `aiAssistantApi.ts`.
- Route `/copilote`, nav « AI Assistant ».
- Typecheck `tsc -b` OK · vitest verts.

### ✔ Feedback

- `POST /api/ai/feedback` : useful / useless / incorrect + commentaire.
- Persistance `elfis_assistant_feedback` + événement bus.
- UI : trois boutons sous chaque réponse assistant.
- Vérifié par `test_api.py::test_history_and_feedback`.

### ✔ Documentation

- `docs/ai/ai-financial-assistant-v1.md`
- `frontend/docs/ai-financial-assistant-v1-certification.md` (ce document)

### ✔ Tests verts

Backend — `python -m pytest tests/ai_assistant -q` :

```
20 passed
```

Frontend — `npx tsc -b` : 0 erreur · `npm test` :

```
Test Files  19 passed (19)
Tests       69 passed (69)
```

## Compléments mission

| Exigence | Couverture |
|----------|------------|
| Mémoire conversationnelle | `elfis_assistant_messages` + préférences |
| Observabilité | `elfis_assistant_runs` (latence, tokens, coût, outils, cache) |
| Cache intelligent | TTL 45 s, fingerprint données |
| Streaming | SSE `stream=true` / `stream_chat()` |
| Actions | Dashboard, factures, transactions, rappel*, rapport* (*confirmation) |

## Verdict

**AI FINANCIAL ASSISTANT V1 CERTIFIED**

# Runbook — Incident provider IA

## Objectif
Couper ou dégrader l’IA en urgence (coût / erreurs / fuite).

## Désactivation d’urgence
1. `ELFIS_AI_ENABLED=false` (ou équivalent) + redémarrage API/workers.
2. Vérifier qu’aucun job AI n’est claim en masse.
3. Surveiller quotas / facturation OpenAI.

## Diagnostic
- Timeouts / 429 provider
- `last_error` scrubbé (pas de prompt ni clé)
- Budgets tokens

## Remédiation
- Réduire `max_tokens` / modèle
- Réactiver progressivement sur staging puis prod
- Rotation `OPENAI_API_KEY` si nécessaire

## Ne jamais
- Fallback silencieux vers un modèle plus coûteux
- Logger prompts ou réponses complètes

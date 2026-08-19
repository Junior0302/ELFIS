# Modèle de rapport d’anomalie — Recette ELFIS

| Champ | Valeur |
|-------|--------|
| ID anomalie | BUG-YYYYMMDD-XXX |
| Sévérité | BLOCKER / CRITICAL / MAJOR / MINOR / COSMETIC |
| Module | Auth / Billing / Vault / DI / AI / Accounting / Search / Notifications / Delivery / Admin / Security / Observability / Reliability |
| Environnement | test-functional / staging |
| Scénario | FUNC-XXX-YYY |
| Étapes de reproduction | 1. … 2. … |
| Résultat attendu | |
| Résultat obtenu | |
| request_id | |
| correlation_id | |
| Captures | (chemins / liens) |
| Logs filtrés | (sans secrets, tokens, payloads Stripe, prompts) |
| Hypothèse | |
| Statut | open / in_progress / fixed / verified / wontfix |
| Responsable | |
| Correction | |
| Test de non-régression | (fichier pytest / ID checklist) |

## Sévérités

- **BLOCKER** : empêche toute recette / perte données / faille sécurité critique
- **CRITICAL** : parcours métier principal cassé
- **MAJOR** : fonction importante dégradée avec contournement
- **MINOR** : impact limité
- **COSMETIC** : UI / texte sans impact fonctionnel

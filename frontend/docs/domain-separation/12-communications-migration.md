# 12 — Communications migration

## Surface

- `/platform/communications` — état provider, connexions org
- `/platform/communications/settings` — distinction infra vs modèles métier

## Données

- `api.listEmailConnections` (org) — status, provider, email, erreurs contrôlées
- `api.platformEmailStatus` — **admin plateforme seulement**
- **Jamais** : clé API, SMTP password, tokens

## ComptaPilot

- Envoi métier inchangé (`email.send` via backend)
- Si envoi indisponible → lien **Communications ELFIS Core**
- Modèles sujet/message facture restent dans `/settings`

## Dette S1.2

- UI complète de configuration connexions (OAuth / SMTP form) côté Core
- Historique global e-mails unifié

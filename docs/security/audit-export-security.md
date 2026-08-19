# Export sécurisé Audit Engine (RC2.3 étape 3)

## Endpoint

`GET /api/admin/audit/export?format=csv|jsonl&…filtres`

Permission : **`security.audit.export`**

## Limites

| Variable | Défaut |
|----------|--------|
| `AUDIT_EXPORT_MAX_ROWS` | 10 000 |
| `AUDIT_EXPORT_MAX_RANGE_DAYS` | 31 |
| `AUDIT_EXPORT_TIMEOUT_SECONDS` | 60 |

Refus `422` si hors limites (`export_too_large`, `date_range_too_large`).

## Sécurité du contenu

- Streaming (pas de fichier serveur exposé)
- UTF-8
- IP masquée (`a.b.*.*`)
- `metadata` sanitisée (pas de password / JWT / secrets)
- Message redigé
- **CSV injection** : cellules commençant par `= + - @` préfixées de `'`

## Audit de l’export

Actions journalisées (sans contenu exporté) :

- `AUDIT_EXPORT_REQUESTED`
- `AUDIT_EXPORT_COMPLETED` (row_count, format, filtres non sensibles)
- `AUDIT_EXPORT_FAILED`

## Rôles

- `platform_admin` : export autorisé
- `platform_operator` / `viewer` / support : **pas** d’export par défaut
- `super_admin` : toutes permissions

## Frontend

Bouton **Exporter CSV** sur `/elfadmin/activity` (visible pour platform admin).  
Confirmation si volume > 1000. Pas de purge / archivage depuis l’UI.

# Audit & Activity Engine (RC2.3 étape 1)

Infrastructure backend unifiée pour journaliser les activités plateforme ELFIS Core.

## Objectif

Fournir un moteur d’audit réutilisable par tous les modules (IAM, Auth, System Health, billing, ComptaPilot, …) **sans** :

- UI / timeline / dashboard avancés (Activity Center lecture = étape 2)
- export
- permissions dans le JWT
- interruption des actions métier en cas d’échec d’écriture

## Architecture

```
app/audit/
  audit_types.py        # Severity, Status, Category, Action
  audit_event.py        # DTO brouillon
  audit_models.py       # ElfisAuditEvent → elfis_audit_events
  audit_repository.py   # insert / list / count / find / stats
  audit_service.py      # record() non bloquant
  audit_context.py      # contexte optionnel (acteur, corr, IP…)
  audit_logger.py       # helpers métier
  audit_filters.py      # filtres lecture
  audit_sanitize.py     # anti-secrets
  audit_dependencies.py # require security.audit.read
  audit_exceptions.py
```

Table SQL : `backend/sql/elfis_audit_events_postgres.sql`  
Migration : `scripts/rc1/migrate_sql.py` (+ `create_all` ORM).

Distinct de :

- `audit_logs` (legacy SaaS)
- `elfis_admin_audit_logs` (Platform Admin enrichi)

## Types

| Enum | Valeurs |
|------|---------|
| Severity | TRACE, INFO, WARNING, ERROR, CRITICAL |
| Status | SUCCESS, FAILURE, PARTIAL |
| Category | AUTH, IAM, SYSTEM, SECURITY, BILLING, PRODUCT, ORGANIZATION, COMPTAPILOT, AI, OCR, NOTIFICATION, EVENT, JOB, … |
| Action (canonique) | LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, ROLE_ASSIGNED, ROLE_REMOVED, PERMISSION_DENIED, HEALTH_REFRESH, … |

## Service

```python
from app.audit import AuditService, AuditLogger

svc = AuditService()  # écritures isolées (SessionLocal)
svc.record("LOGIN_SUCCESS", actor_user_id=1, category="AUTH")

# Ou helpers
AuditLogger().record_role_assignment(target_user_id=2, role_code="platform_viewer")
```

Règles :

1. `record()` capture toute exception d’écriture → log warning → retourne `None`
2. Écritures isolées par défaut (`isolated_writes=True`) pour ne pas contaminer une transaction métier
3. Mode test : `AuditService(db, isolated_writes=False)` + SAVEPOINT (`begin_nested`)
4. `record_async` existe pour compatibilité async (écriture sync SQLAlchemy)

## Contexte

`AuditContext` / `current_audit_context()` s’appuie sur `request_id` / `correlation_id` observability. Tous les champs sont optionnels.

## API (lecture seule)

Préfixe : `/api/admin/audit`

| Méthode | Route | Permission |
|---------|-------|------------|
| GET | `/events` | `security.audit.read` |
| GET | `/events/{id}` | `security.audit.read` |
| GET | `/statistics` | `security.audit.read` |

Filtres query : `date_from`, `date_to`, `hours`, `severity`, `category`, `actor_user_id`, `actor_email`, `organization_id`, `service`, `product`, `action`, `status`, `success`, `limit` (défaut 25, max 100), `offset`.

Réponse liste : `{ total, limit, offset, items }` — tri `occurred_at` descendant.

Statistiques enrichies (compatibles) : `permission_denied`, `login_failure`, `iam_changes`, `warnings_errors`, `hours`.

Détail : inclut `ip_address`, `user_agent` (affichage masqué côté UI).

## Activity Center (étapes 2–3)

UI : `/elfadmin/activity` — voir `docs/platform/activity-center.md`.

Étape 3 :
- recherche avancée (`q`, cibles, correlation_id, plage personnalisée)
- export CSV/JSONL (`security.audit.export`) — `docs/security/audit-export-security.md`
- rétention / archive CLI — `docs/security/audit-retention-policy.md`
- indexes composites + table `elfis_audit_events_archive`
- **pas** de pagination cursor (offset/limit suffisant ; documenté)

## Premières intégrations

| Module | Événements |
|--------|------------|
| Auth | LOGIN_SUCCESS (`_issue_session`), LOGIN_FAILURE (Firebase), LOGOUT (`POST /api/auth/logout`) |
| IAM | ROLE_ASSIGNED / ROLE_REMOVED (`PlatformRoleService._audit`) |
| IAM deps | PERMISSION_DENIED (`_log_denial`) |
| System Health | HEALTH_REFRESH (`GET /api/admin/system/health`) |

## Sécurité

Jamais enregistrer : JWT, mots de passe, secrets, API keys, tokens Stripe, cookies, secrets Vault, texte OCR, prompts / réponses IA complètes.

Protection : `audit_sanitize.sanitize_metadata` + redaction `app.security.security_redaction`.

## Bonnes pratiques

- Appeler `AuditLogger` / `AuditService.record` **après** le succès métier (sauf FAILURE explicite)
- Ne jamais `raise` depuis un bridge d’audit
- Préférer des metadata courtes (ids, codes) plutôt que des payloads
- Utiliser `correlation_id` pour relier les événements d’une même requête
- Ne pas mettre de droits dans le JWT : l’audit lit/écrit côté serveur uniquement

## Limites (étape 1)

- Pas d’UI
- Pas de retention / purge automatique
- Pas d’export
- Pas de remplacement des tables d’audit existantes
- Helpers JOB_RETRY / EVENT_RETRY / billing / invoice préparés mais non branchés hors Auth/IAM/Health

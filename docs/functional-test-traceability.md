# Matrice de traçabilité — Recette fonctionnelle

| Fonctionnalité | Route backend | Page frontend | Test auto | Test manuel | Permission | Entitlement | Quota | Event | Job | Notification |
|----------------|---------------|---------------|-----------|-------------|------------|-------------|-------|-------|-----|--------------|
| Auth session | GET /api/auth/me | Login / Dashboard | test_authentication_flow | FUNC-AUTH-001 | — | — | — | — | — | — |
| Isolation tenant | GET /api/vault/documents + X-Organization-Id | Documents | test_tenant_isolation_flow | FUNC-AUTH-002 | documents.read | documents.vault | — | — | — | — |
| Essai gratuit | subscriptions / billing | Abonnement | test_trial_flow | FUNC-BILL-001 | subscription.manage | — | — | — | — | — |
| Abo actif | legacy Subscription + elfis_subscriptions | Abonnement | test_trial_flow | FUNC-BILL-002 | subscription.manage | documents.upload | documents.processed.month | — | billing.sync_subscription.v1 | — |
| Upload document | POST /api/vault/documents/archive | Dépôt / Documents | test_document_flow | FUNC-DOC-001 | documents.write | documents.upload | documents.processed.month | vault.document.archived.v1 | vault.document.extract_text.v1 | — |
| Analyse IA | /api/ai / jobs | Intelligence | (mocks + DI/AI suites) | FUNC-DOC-001 | ai.analysis | ai.classification | ai.executions.month | — | vault.document.ai_* | — |
| Proposition comptable | /api/accounting/proposals | Comptabilité | test_accounting_flow | FUNC-ACC-001 | documents.read | accounting.proposals | — | accounting.proposal.* | accounting.build_proposal.v1 | — |
| Envoi e-mail | delivery / mailer | Facturation | test_delivery_flow | FUNC-DEL-001 | documents.send_email | email.send | emails.sent.month | — | — | email sent |
| Recherche | GET /api/search | Search | test_search_flow | FUNC-SEA-001 | documents.read | search.global | search.queries | search.* | search.index_resource.v1 | — |
| Notifications | GET /api/notifications | Notifications | (suite notifications) | FUNC-NOT-001 | — | notifications.in_app | — | — | — | in_app |
| Quota atteint | billing guards | — | test_billing_flow | FUNC-BILL-004 | — | — | documents.processed.month | — | — | usage warning |
| Org suspendue | require_active_subscription | — | test_admin_flow | FUNC-ORG-001 | — | costly features off | — | platform.organization.suspended.v1 | — | — |
| Admin dashboard | GET /api/platform/dashboard | /elfadmin | test_admin_flow | FUNC-ADM-001 | platform | — | — | — | — | — |
| Security config | GET /api/platform/security/configuration | /elfadmin/securite | test_admin_flow | FUNC-SEC-001 | platform | — | — | — | — | — |
| Health live/ready | /api/health/live\|ready | — | test_security_flow | FUNC-OBS-001 | — | — | — | — | reliability.check_system_health.v1 | — |
| Correlation IDs | middleware | — | test_security_flow | FUNC-SEC-001 | — | — | — | — | — | — |
| Retry IA | jobs | — | test_failure_recovery_flow | FUNC-ERR-001 | — | — | — | — | * | — |

## Notes

- Les parcours Document→IA→Accounting complets dépendent des workers ; lancer job/event workers pour la checklist manuelle async.
- Enforcement entitlements/quotas off par défaut ; activer pour FUNC-BILL-004.

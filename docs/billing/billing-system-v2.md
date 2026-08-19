# Billing System V2 — ELFIS Core

## Principe

Le **Billing Engine** (Entitlement Engine + plans + quotas + abonnements `elfis_*`) est la **seule source de vérité** pour :

- statut d’abonnement / essai
- fonctionnalités (entitlements)
- quotas et consommation
- droits d’accès produit

**Stripe** reflète et synchronise les paiements (Checkout, portail, webhooks). Il ne décide pas de la logique métier.

La facturation commerciale (devis / factures clients) reste un domaine distinct sous `/api/billing/sales-overview`, `/customers`, `/documents`, etc.

## Audit (réutilisation)

| Zone | Statut |
|------|--------|
| `backend/app/billing/*` | Core V1 → étendu V2 |
| Stripe (`stripe_service`, webhooks legacy) | Réutilisé |
| `subscriptions` legacy | Sync → `elfis_subscriptions` |
| Notifications Event Bus | Handlers billing |
| Platform admin `/platform/billing/*` | Cockpit finance |
| IAM `subscription.manage` | Checkout / portail |

## Entitlement Engine

Facade : `app.billing.entitlement_engine.EntitlementEngine`

```python
state = EntitlementEngine(db).resolve(organization_id)
engine.require_feature(org_id, FeatureCodes.AI_CLASSIFICATION, user=user)
engine.check_quota(org_id, QuotaCodes.AI_EXECUTIONS_MONTH)
```

État unique : `trialing` / `active` / `past_due` / `cancelled` / `suspended` / `expired` (+ enterprise via plan).

## Plans (catalogue)

Registre : `plan_registry.py` — **Starter**, **Professional** (public), **Enterprise** (privé / devis).

- Prix catalogue pour UI / MRR — **pas** de price_id inventé côté client
- Price Stripe uniquement via settings / env (`stripe_price_*`)

## Essai

- Un essai par organisation (règles legacy + engine)
- Début / fin / jours restants / conversion / expiration

## Quotas

Centralisés : documents, users, storage, IA, emails, OCR (via features), etc.

API : utilisé / restant / limite / % (`QuotaService.check`).

## API SaaS

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/api/billing/overview` | État org (engine) |
| GET | `/api/billing/plans` | Catalogue public |
| GET | `/api/billing/subscription` | Abonnement |
| GET | `/api/billing/usage` | Usage |
| GET | `/api/billing/quotas` | Quotas |
| GET | `/api/billing/history` | Historique |
| GET | `/api/billing/webhooks` | Audit événements (sans secrets) |
| POST | `/api/billing/checkout` | Checkout Stripe |
| POST | `/api/billing/customer-portal` | Portail |
| GET | `/api/platform/billing/overview` | MRR / ARR cockpit |
| GET | `/api/platform/billing/subscriptions` | Liste admin |
| POST | `/api/platform/billing/subscriptions/{id}/suspend\|restore` | Admin audité |

Webhooks ingest (signés) :

- `/api/subscriptions/webhook`
- `/api/webhooks/stripe`

Idempotence : table `elfis_billing_events` + hash payload.

## Frontend

- `/abonnement` — onglets : Mon abonnement, Consommation, Historique, Paiements, Changer de plan
- `/elfadmin/abonnements` — Billing Cockpit (MRR/ARR, filtres, suspend/restore)

## Sécurité

- Isolation tenant via `organization_id` auth
- Pas de secrets Stripe exposés au frontend
- Actions admin journalisées (`write_audit`)
- Webhooks signés Stripe

## Flags

- `elfis_billing_enforce_entitlements`
- `elfis_billing_enforce_quotas`

## Certification

Voir `frontend/docs/billing-system-v2-certification-report.md`.

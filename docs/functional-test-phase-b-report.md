# Rapport Phase B — Billing, essai, abonnements, entitlements, quotas

Date : 2026-07-20  
Environnement : `ELFIS_ENVIRONMENT=test` · mocks Stripe (aucun réseau)  
Commande : `python scripts/run_functional_validation.py --phase-b`  
Commit / push : **aucun**

---

## 1. Cartographie Billing

| Composant | Emplacement | Rôle |
|-----------|-------------|------|
| Plan registry | `app/billing/plan_registry.py` | starter 19 € / 14 j public ; pro/enterprise non publics |
| SubscriptionService | `app/billing/subscription_service.py` | sync legacy → `elfis_subscriptions`, grâce 7 j |
| EntitlementService | `app/billing/entitlement_service.py` | features + overrides + past_due read_only |
| QuotaService / UsageService | `app/billing/quota_*.py` / `usage_service.py` | quotas atomiques, usage agrégé |
| StripeService | `app/billing/stripe_service.py` | façade unique → `stripe_billing` |
| Webhooks | `/api/subscriptions/webhook` + `/api/webhooks/stripe` | même handler `_handle_stripe_webhook` |
| Accès runtime | `app/subscriptions/access.py` + `deps.require_active_subscription` | lit table **legacy** |
| Enforcement | `ELFIS_BILLING_ENFORCE_*` | **off** par défaut ; ON dans tests ciblés |

**États seed testés :** ORG_NONE, ORG_TRIAL, ORG_ACTIVE, ORG_PAST_DUE, ORG_PAST_DUE_EXPIRED, ORG_CANCELLED, ORG_EXPIRED, ORG_QUOTA_NEAR, ORG_QUOTA_FULL, ORG_SUSPENDED, ORG_SECOND_TENANT.

---

## 2. Événements Stripe simulés

- `checkout.session.completed`
- `customer.subscription.created` / `updated` / `deleted`
- `invoice.payment_succeeded` / `payment_failed`
- Duplicat idempotent (`provider_event_id`)
- Signature invalide / Stripe non configuré → refus (400/401/403/503)

---

## 3. Plans / entitlements / quotas

- **Starter** : 19 EUR, trial 14 j, public, achetable  
- **Professional / Enterprise** : non publics, non achetables sans price  
- Features : upload, AI, accounting, search, email (matrices plan)  
- Quotas : documents (near 80 %, full 100 %), AI illimité starter, override limite  

---

## 4. Anomalies

### PHB-B-001 — Divergence grâce past_due 3 j vs 7 j

| Champ | Valeur |
|-------|--------|
| **ID** | PHB-B-001 |
| **Sévérité** | CRITICAL |
| **Module** | Billing / Access |
| **Scénario** | PASTDUE-003 |
| **Cause** | `access.py` utilisait `stripe_past_due_grace_days=3` alors que Billing V1 utilise `elfis_billing_past_due_grace_days=7` → J+4 incohérent |
| **Correction** | Accès unifié sur `elfis_billing_*` (fallback 7) ; défauts config + `.env.example` à 7 ; notification `grace_until` = past_due + N jours |
| **Fichiers** | `access.py`, `config.py`, `stripe_billing.py`, `.env.example`, `test_stripe_billing.py` |
| **Test** | `test_pastdue_003_harmonized_7_days_day4_still_grace` |
| **Résultat** | PASS |
| **Risque résiduel** | Un `.env` local ancien avec `STRIPE_PAST_DUE_GRACE_DAYS=3` est ignoré pour l’accès si `elfis_billing_past_due_grace_days=7` |

### PHB-B-002 — Seed sans user pour ORG_EXPIRED / ORG_PAST_DUE_EXPIRED

| Champ | Valeur |
|-------|--------|
| **Sévérité** | MINOR |
| **Correction** | Comptes `expired@` et `pastdue.expired@` ajoutés au catalogue |
| **Fichier** | `tests/functional/catalog.py` |

---

## 5. Politique de grâce finale

**7 jours** uniques (`ELFIS_BILLING_PAST_DUE_GRACE_DAYS` / `STRIPE_PAST_DUE_GRACE_DAYS`).  
Pendant la grâce : `has_access=True`, `read_only=True` → lectures OK, écritures / features coûteuses bloquées.  
Après J+7 : accès métier bloqué ; portail / plans / checkout restent disponibles.

---

## 6. Notifications Billing

| Type | Statut |
|------|--------|
| payment_failed | Implémentée (legacy notify) |
| trial / activated / cancel | Préparées via events domain |
| quota near/full | Préparées (seuils config) |
| Doublons webhook | Idempotence `provider_event_id` |

---

## 7. Fichiers créés / modifiés

**Créés**

- `tests/functional/helpers/phase_b.py`
- `tests/functional/scenarios/test_phase_b_*.py` (11 fichiers)
- `docs/functional-test-phase-b-report.md`

**Modifiés**

- `app/subscriptions/access.py`, `app/config.py`, `app/services/stripe_billing.py`
- `tests/test_stripe_billing.py`, `tests/functional/catalog.py`, `tests/functional/conftest.py`
- `scripts/run_functional_validation.py` (`--phase-b`)
- `.env.example`, checklist, how-to-run

---

## 8. Résultats

| Suite | Résultat |
|-------|----------|
| Phase B scenarios | **47 passed** |
| Billing + Stripe + access | **35 passed** |
| FastAPI import | **OK** (240 routes) |
| Frontend build | **OK** |
| Appels Stripe / réseau | **0** |
| Issues billing critiques restantes | **0** |

---

## 9. Limites & manuels

- Checkout réel Stripe Test : manuel (UI)
- Notifications e-mail réelles : hors scope (mock)
- Tokens IA depuis `elfis_ai_usage` : couverts via UsageService ; pas d’appel OpenAI
- Firebase / AbonnementPage : checklist manuelle Phase B

---

## 10. Matrice PASS

```
Plans.......................... PASS
Trial 14 days.................. PASS
Active subscription............ PASS
Legacy synchronization......... PASS
Stripe webhook processing...... PASS
Webhook idempotency............ PASS
Webhook security............... PASS
Past-due grace.................. PASS
Cancellation / resume.......... PASS
Expiration..................... PASS
Entitlements................... PASS
Quotas......................... PASS
Usage aggregation.............. PASS
Billing tenant isolation....... PASS
Billing admin.................. PASS
Billing notifications.......... PASS

Phase B functional tests........ 47 passed
Regression tests............... 35 passed
FastAPI import................. OK
Frontend build................. OK
Real Stripe calls.............. 0
Known critical billing issues.. 0
```

# Runbook — Incident Stripe

## Objectif
Contenir un incident paiement / webhook sans double facturation.

## Symptômes
- Pic `payment_failed`
- Webhooks signature invalide
- Abonnements désynchronisés
- Checkout 5xx

## Actions immédiates
1. Vérifier `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` (pas d’exposition logs).
2. Mettre l’API en mode lecture si critique (feature flag billing si disponible).
3. **Ne pas** rejouer massivement des events sans contrôle idempotence `provider_event_id`.
4. Consulter Dashboard Stripe (mode live vs test cohérent).

## Diagnostic
- Compter webhooks `received` vs `processed` / `failed`
- Vérifier index unique `uq_elfis_billing_provider_event`
- Logs scrubbés uniquement

## Remédiation
- Corriger secret / endpoint webhook
- Retry ciblé events failed
- Communication client si paiements impactés

## Ne jamais
- Désactiver la vérification de signature
- Appliquer deux fois le même `provider_event_id`

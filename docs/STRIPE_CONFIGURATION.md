# Configuration Stripe — ComptaPilot IA

## Variables d’environnement

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_TRIAL_DAYS=14
STRIPE_PAST_DUE_GRACE_DAYS=3
FRONTEND_URL=https://elfis-core.com
SUBSCRIPTION_TERMS_VERSION=v1
SUBSCRIPTION_CRON_TOKEN=long-random-token
```

## Produit / prix

1. Créer le produit **ComptaPilot IA**.
2. Créer un prix récurrent **19,00 EUR / mois**.
3. Copier l’ID `price_...` dans `STRIPE_PRICE_PRO`.

## Webhooks

URL production (au choix, même handler) :

- `https://elfis-core-api.onrender.com/api/subscriptions/webhook`
- `https://elfis-core-api.onrender.com/api/webhooks/stripe`

Événements recommandés :

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `customer.subscription.trial_will_end`
- `invoice.paid`
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `invoice.payment_action_required`

## Local

```bash
stripe listen --forward-to http://127.0.0.1:8001/api/subscriptions/webhook
```

## Rappels d’essai (cron)

```bash
curl -X POST https://elfis-core-api.onrender.com/api/subscriptions/jobs/trial-reminders \
  -H "Content-Type: application/json" \
  -d '{"token":"$SUBSCRIPTION_CRON_TOKEN"}'
```

# Système d’abonnement ComptaPilot IA

## Architecture

- **Portée** : un abonnement Stripe par **organisation** (pas par utilisateur).
- **Source de vérité paiement** : Stripe.
- **Source de vérité droits métier** : base interne (`subscriptions` + `get_subscription_access`).
- **Gate premium** : `require_active_subscription` → délègue à `app.subscriptions.access`.

## Module central

```text
backend/app/subscriptions/
  access.py          # get_subscription_access / serialize_access
  permissions.py     # can_access_feature / entitlements
  constants.py       # plan, prix, libellés, codes erreur
  consent.py         # consentement checkout + éligibilité essai
  notifications.py   # emails / déduplication / rappels
  admin_actions.py   # revoke / restore / grant_trial
  messages.py        # textes utilisateur
```

Stripe bas niveau reste dans `backend/app/services/stripe_billing.py`.

## Statuts UX

| Statut | Signification |
|--------|----------------|
| `none` | Pas d’abo |
| `checkout_pending` | Session incomplete |
| `trialing` | Essai |
| `active` | Payant actif |
| `cancel_scheduled` | `cancel_at_period_end` + accès jusqu’à fin de période |
| `past_due` | Impayé (+ grâce lecture seule) |
| `admin_revoked` | Suspension admin (prioritaire) |
| `canceled` / `expired` | Terminé |

## Endpoints

- `GET /api/subscriptions/current`
- `GET /api/subscriptions/plan`
- `POST /api/subscriptions/checkout` (consentements obligatoires)
- `POST /api/subscriptions/portal`
- `POST /api/subscriptions/sync`
- `POST /api/subscriptions/webhook`
- `POST /api/webhooks/stripe` (alias)
- `POST /api/subscriptions/jobs/trial-reminders` (token cron)

## Essai unique

Champs `trial_used`, `trial_eligibility_status` (`eligible` | `already_used` | `admin_granted`).  
Réabonnement possible sans nouvel essai ; un admin peut réattribuer (`admin_granted`).

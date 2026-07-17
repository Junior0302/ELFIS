# Plan de tests — Abonnements

## Automatisés

```bash
cd backend
python -m pytest tests/test_stripe_billing.py tests/test_subscription_access.py -q
```

## Scénarios manuels (Stripe Test)

1. Visiteur → register → `/abonnement` sans abo (`none`).
2. Consentements non cochés → checkout refusé.
3. Consentements OK → Checkout essai 14 j (carte `4242…`).
4. Retour success → sync → `trialing` + accès dashboard.
5. Double clic checkout avec abo actif → 409.
6. Webhook dupliqué → `duplicate: true`.
7. Signature invalide → 400.
8. Annulation portail `cancel_at_period_end` → statut UX `cancel_scheduled`.
9. Paiement échoué → `past_due` + lecture seule pendant grâce.
10. Admin revoke → accès coupé + motif public.
11. Admin grant trial → nouvel essai possible.
12. Cron `trial-reminders` avec token → 200.

## Non-régression

- OCR / facturation / CRM / copilote restent gateés par abo.
- ELF Admin bypass toujours actif.

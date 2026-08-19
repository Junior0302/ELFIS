# Billing System V2 — Rapport de certification

**Produit :** ELFIS Core / ComptaPilot IA  
**Date :** 2026-07-18  
**Version engine :** 2.0.0  

## Verdict

**BILLING SYSTEM V2 CERTIFIED**

| Critère | Statut |
|---------|--------|
| Billing Engine = source de vérité | OK (`EntitlementEngine.resolve`) |
| Stripe synchronise, ne pilote pas le métier | OK (webhooks → sync `elfis_*`) |
| Quotas | OK (`QuotaService` + UI consommation) |
| Essais | OK (statut trialing + jours restants) |
| Plans Starter / Professional / Enterprise | OK (`plan_registry`) |
| Droits via entitlements | OK (guards + IAM `subscription.manage`) |
| Webhooks idempotents | OK (`elfis_billing_events`) |
| Build frontend | OK (`npm run build`) |
| Tests billing | OK (25/25) |

## Livrables

- Entitlement Engine + overview org / platform MRR-ARR
- API `/billing/overview|plans|subscription|usage|quotas|history|webhooks`
- Facturation commerciale déplacée vers `/billing/sales-overview` (évite collision)
- Pages FE abonnement (onglets V2) + cockpit admin abonnements
- Notifications : essai, paiement, suspension, réactivation, changement de plan
- Docs : `docs/billing/billing-system-v2.md`

## Sécurité (revue)

- Aucun secret Stripe dans les réponses FE
- Portail / checkout côté serveur
- Suspend / restore admin audités

## Notes

- Les flags `elfis_billing_enforce_*` peuvent être désactivés en environnement ; le moteur reste la source de vérité des états.
- MRR/ARR = catalogue × abonnements engine (pas Stripe live).

# Runbook — Rotation des secrets

## Objectif
Remplacer JWT, Stripe, mailer, storage, Firebase sans downtime incontrôlé.

## Principes
- Générer le nouveau secret hors dépôt
- Déployer la config qui accepte ancien + nouveau si possible (période de dualité)
- Révoquer l’ancien après validation
- Ne jamais logger la valeur

## JWT
1. Générer secret ≥ 32 caractères cryptographiquement fort.
2. Déployer `JWT_SECRET` (sessions existantes invalidées — prévenir les users).
3. Vérifier login staging puis production.
4. Surveiller 401.

## Stripe
1. Créer nouvelle clé secrète / webhook secret dans le Dashboard.
2. Mettre à jour `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
3. Vérifier signature webhook (événements test staging).
4. Révoquer ancienne clé.
5. Cohérence live/test : ne pas mélanger `sk_live` et price `test`.

## Mailer (Brevo / SMTP)
1. Nouvelle clé API / mot de passe SMTP.
2. Mettre à jour variables ; redémarrer API/workers.
3. Envoyer un mail de sonde **staging uniquement**.
4. Révoquer ancienne clé.

## Storage (Supabase)
1. Rotation service role via console.
2. Mettre à jour `SUPABASE_SERVICE_ROLE_KEY`.
3. Vérifier upload/download staging.
4. Révoquer ancien.

## Firebase
1. Rotation selon console Google.
2. Mettre à jour clés web / admin selon architecture.
3. Valider auth staging.

## Contrôles
- `validate_production_config.py` ok
- aucun secret dans logs (`check_secrets.py` sur le dépôt après coup)
- health ready

## Escalade
Si auth massivement cassée → rollback secret précédent depuis coffre + incident.

## Ne jamais
- Committer le nouveau secret
- Coller le secret dans un ticket / chat non chiffré

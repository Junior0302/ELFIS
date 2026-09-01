-- BANK-5 — consent lifecycle, expiration SCA, réauthentification
-- Appliqué par scripts/rc1/migrate_sql.py (SQL_ORDER). Idempotent.
-- Additive uniquement : aucune suppression, aucun secret, aucune réponse fournisseur brute.
--
-- Le mot "duplicate" est volontairement absent du RAISE : migrate_sql.py
-- tolère les messages contenant "duplicate" / "already exists".

DO $$
BEGIN
  IF to_regclass('public.elfis_bank_connections') IS NULL THEN
    RETURN;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'authentication_expires_at'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN authentication_expires_at TIMESTAMP WITHOUT TIME ZONE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'reauth_required_at'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN reauth_required_at TIMESTAMP WITHOUT TIME ZONE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'reauth_reason'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN reauth_reason VARCHAR(64);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'last_reauth_at'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN last_reauth_at TIMESTAMP WITHOUT TIME ZONE;
  END IF;
END $$;

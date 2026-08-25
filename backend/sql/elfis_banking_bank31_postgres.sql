-- BANK-3.1 — identité provider concurrent-safe (Postgres existant)
-- Appliqué par scripts/rc1/migrate_sql.py (SQL_ORDER). Idempotent.
-- Additive uniquement : aucun DELETE, aucune fusion, aucune contrainte sur fingerprint.
--
-- external_id manquant est stocké '' (convention BANK-3). L'index unique ignore
-- les identifiants vides pour conserver plusieurs observations distinctes.
--
-- Le mot "duplicate" est volontairement absent du RAISE : migrate_sql.py
-- tolère les messages contenant "duplicate" / "already exists".

DO $$
DECLARE
  uncanonical_count integer := 0;
  conflict_count integer := 0;
BEGIN
  IF to_regclass('public.bank_transactions') IS NULL THEN
    RETURN;
  END IF;

  SELECT COUNT(*) INTO uncanonical_count
    FROM bank_transactions
   WHERE external_id IS NOT NULL
     AND external_id <> btrim(external_id);

  IF uncanonical_count > 0 THEN
    RAISE EXCEPTION
      'BANK-3.1: % bank_transactions rows have non-canonical provider external_id (not trimmed); unique index not created',
      uncanonical_count;
  END IF;

  SELECT COUNT(*) INTO conflict_count
    FROM (
      SELECT account_id, btrim(external_id) AS canonical_external_id
        FROM bank_transactions
       WHERE btrim(COALESCE(external_id, '')) <> ''
       GROUP BY account_id, btrim(external_id)
      HAVING COUNT(*) > 1
    ) conflicts;

  IF conflict_count > 0 THEN
    RAISE EXCEPTION
      'BANK-3.1: % conflicting bank_transactions groups share account_id and trimmed provider external_id; unique index not created',
      conflict_count;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.bank_transactions') IS NULL THEN
    RETURN;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_bank_transactions_external_id_trimmed'
  ) THEN
    ALTER TABLE bank_transactions
      ADD CONSTRAINT ck_bank_transactions_external_id_trimmed
      CHECK (external_id IS NULL OR external_id = btrim(external_id));
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_bank_transactions_account_external_id
    ON bank_transactions (account_id, external_id)
    WHERE btrim(COALESCE(external_id, '')) <> '';

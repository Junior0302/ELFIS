-- BANK-4 — synchronisation automatique, état de sync, receipts webhook
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
       AND column_name = 'last_sync_started_at'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN last_sync_started_at TIMESTAMP WITHOUT TIME ZONE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'last_sync_status'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN last_sync_status VARCHAR(16) NOT NULL DEFAULT 'never';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'last_sync_error_code'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN last_sync_error_code VARCHAR(64);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'elfis_bank_connections'
       AND column_name = 'consecutive_sync_failures'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD COLUMN consecutive_sync_failures INTEGER NOT NULL DEFAULT 0;
  END IF;
END $$;

DO $$
BEGIN
  IF to_regclass('public.elfis_bank_connections') IS NULL THEN
    RETURN;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_elfis_bank_connections_last_sync_status'
  ) THEN
    ALTER TABLE elfis_bank_connections
      ADD CONSTRAINT ck_elfis_bank_connections_last_sync_status
      CHECK (last_sync_status IN ('never', 'queued', 'syncing', 'success', 'failed'));
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS elfis_bank_webhook_receipts (
    id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR(32) NOT NULL,
    provider_event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'received',
    organization_id INTEGER,
    connection_id INTEGER,
    job_id VARCHAR(36),
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_bank_webhook_provider_event
    ON elfis_bank_webhook_receipts (provider, provider_event_id);

CREATE INDEX IF NOT EXISTS ix_elfis_bank_webhook_receipts_org
    ON elfis_bank_webhook_receipts (organization_id);

CREATE INDEX IF NOT EXISTS ix_elfis_bank_webhook_receipts_connection
    ON elfis_bank_webhook_receipts (connection_id);

-- BANK-2.1 — colonnes soldes / type de compte (Postgres existant)
-- Appliqué par scripts/rc1/migrate_sql.py (SQL_ORDER). Idempotent.
-- Additive uniquement : aucune suppression de colonne ou de table, aucune réécriture de lignes.

ALTER TABLE bank_accounts
    ADD COLUMN IF NOT EXISTS account_type VARCHAR(32) NOT NULL DEFAULT 'other';
ALTER TABLE bank_accounts
    ADD COLUMN IF NOT EXISTS available_balance DOUBLE PRECISION;
ALTER TABLE bank_accounts
    ADD COLUMN IF NOT EXISTS balance_updated_at TIMESTAMP WITHOUT TIME ZONE;

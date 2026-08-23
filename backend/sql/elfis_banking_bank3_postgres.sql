-- BANK-3 — enrichissement transactions (Postgres existant)
-- Appliqué par scripts/rc1/migrate_sql.py (SQL_ORDER). Idempotent.
-- Additive uniquement : aucune suppression de colonne ou de table.

-- value_date : date de valeur distincte de booked_at (fournisseur).
ALTER TABLE bank_transactions
    ADD COLUMN IF NOT EXISTS value_date VARCHAR(32);
-- counterparty_name : libellé de contrepartie non sensible (jamais un IBAN).
ALTER TABLE bank_transactions
    ADD COLUMN IF NOT EXISTS counterparty_name VARCHAR(255);
-- reference : référence d'opération fournisseur / bout-à-bout.
ALTER TABLE bank_transactions
    ADD COLUMN IF NOT EXISTS reference VARCHAR(128);

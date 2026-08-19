-- Launch Dashboard V1 — préférence découverte espace comptable

ALTER TABLE organization_members
    ADD COLUMN IF NOT EXISTS accounting_hub_visited_at TIMESTAMP WITHOUT TIME ZONE;

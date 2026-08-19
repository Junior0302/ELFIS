-- RC2.5.6 — élargir statuts delivery (idempotent, non destructif)

ALTER TABLE elfis_product_document_deliveries
    DROP CONSTRAINT IF EXISTS ck_elfis_del_status;

ALTER TABLE elfis_product_document_deliveries
    ADD CONSTRAINT ck_elfis_del_status CHECK (
        status IN (
            'pending','queued','delivering','delivered','retrying',
            'failed','cancelled','blocked','unknown','manual_review',
            'validated_not_delivered'
        )
    );

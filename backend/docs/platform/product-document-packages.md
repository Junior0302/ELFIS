# Product document packages & integrations

- Schéma package : `elfis_document_package_v1`
- Tables : `elfis_product_processing_packages`, `elfis_product_document_deliveries`, `elfis_product_document_delivery_attempts`
- Idempotence : hash(product, org, version, extraction, validation, schema_version)
- API : `/api/product-integrations/*`
- Contenu métier uniquement dans artefact StorageObject privé — absents des listes et audits

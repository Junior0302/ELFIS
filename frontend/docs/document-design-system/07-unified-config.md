# 07 — Config documentaire unique

`DocumentRenderConfig` / `buildDocumentRenderConfig` :

| Champ | Rôle |
|-------|------|
| `showLogo` | Affichage logo |
| `logo` / `logoUrl` | Fichier org |
| `primaryColor` / `secondaryColor` | Accent |
| `template` | `premium_v1` |

Persisté document : `sales_documents.branding_json`.  
Consommé par preview live, PDF download, email, archive Vault (même `sales_document_to_pdf`).

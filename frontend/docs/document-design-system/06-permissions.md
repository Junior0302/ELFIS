# 06 — Permissions

| Action | Permission |
|--------|------------|
| Afficher / masquer logo sur le document | `invoice.create` ou `quote.create` (édition doc) |
| Remplacer / ajouter logo org | `settings.manage` (admin/owner typique) |
| Persister préférence `documents_show_logo` | `settings.manage` |
| Lire PDF | `invoice.read` |

Le Composer ne quitte pas pour l’upload logo (sous-dialog interne).

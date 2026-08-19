# 15 — S1.1 route migration

| Historique | Cible | Propriétaire | Redirect | Compat | Dette |
|------------|-------|--------------|----------|--------|-------|
| `/organisation` | `/platform/organization` | ELFIS | oui | indéfinie | retirer après adoption |
| `/admin/equipe` | `/platform/members` | ELFIS | oui | indéfinie | idem |
| `/team` | `/platform/members` | ELFIS | oui | indéfinie | était settings en S1.0 |
| `/vault` | `/platform/documents` | ELFIS | oui | indéfinie | |
| `/documents` | `/documents` (filtrée) | Compta vue | non | — | filtrage UI |
| `/platform/documents` | nouveau | ELFIS | — | — | |
| `/platform/communications` | nouveau | ELFIS | — | — | |
| `/platform/aura` | nouveau | ELFIS | — | — | |
| `/platform/relations` | nouveau | ELFIS | — | — | |
| `/platform/teams` | `/platform/members` | ELFIS | oui | — | écran dédié futur |
| `/platform/roles` | `/platform/members` | ELFIS | oui | — | idem |
| `/copilote` | `/copilote` | Compta | non | — | lien Aura |
| `/clients` | `/clients` | Compta vue | non | — | |
| `/elfadmin` | inchangé | Admin | — | — | |
| `/platform` → elfadmin | **supprimé** | — | — | — | évite boucle workspace |

Source navigation : ProductAccessLayout (`isPlatformShellPath` → PlatformWorkspaceLayout sauf `/home`).

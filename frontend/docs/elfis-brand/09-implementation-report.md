# 09 — Rapport d’implémentation BRAND.ELFIS.2

**GO** — critères satisfaits. STOP captures / revue. Ne pas démarrer d’autre feature.

## Livrables

| Zone | Changement |
|------|------------|
| Tokens | `--elfis-*` + alias plateforme ; palette `elfis-core` navy-950 / blue-600 |
| Membres | PageHeader ENTREPRISE ; invitation neutre ; ElfisField ; rôles globaux |
| Rôles | Mapping UI cfo→Gestionnaire, comptable/employe→Collaborateur ; cartes 5 rôles |
| Nav | Actif navy clair + marqueur blue-600 ; footer ELFIS / Plateforme (déjà) |
| Docs | `frontend/docs/elfis-brand/` 01–09 |
| Tests | EB01–EB30 |

## Critères GO

1. `/platform/members` identité ELFIS — oui  
2. Plus d’invitation verte Finance — oui  
3. Rôles transversaux — oui  
4. Plus Directeur Finance / Comptable comme libellés globaux — oui  
5. Tokens plateforme — oui  
6. Navy + bleu signature — oui  
7. Accents métier limités — documenté  
8. Permissions backend inchangées (clés) — oui  
9–11. Tests EB01–EB30 verts · `tsc -b` · `npm run build` — **OK** (2026-08-04)  

## Hors scope respecté

Finance / Commercial non refaits. Pas de migration tables. Pas de commit.

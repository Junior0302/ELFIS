# Activity Center (RC2.3 étape 2)

Interface d’administration pour consulter les événements de l’Audit Engine.

## Route

- **UI** : `/elfadmin/activity`
- **Nav** : ELF Admin → *Activity Center*
- **Layout** : `PlatformLayout` (guard `RequirePlatformAdmin`)

La page legacy `/elfadmin/audit` (Platform Admin audit ops) reste distincte.

## Permissions

| Couche | Règle |
|--------|--------|
| Frontend | Shell ELF Admin (`is_platform_admin`) |
| Backend | `security.audit.read` (autorité) |

Les platform admins historiques conservent l’accès via le resolver IAM hybride.

Type frontend : `security.audit.read` dans `types/permissions.ts`.

## API consommée

- `GET /api/admin/audit/events`
- `GET /api/admin/audit/events/{id}`
- `GET /api/admin/audit/statistics`

Service : `frontend/src/services/auditApi.ts`

## Filtres

Période prédéfinie (1 h / 24 h / 7 j / 30 j), catégorie, sévérité, statut, succès/échec, action, acteur (email), organisation, service, produit.

Synchronisation URL via `useSearchParams` (partageable / rechargement).

Bouton **Réinitialiser**.

## Pagination

Serveur `offset` / `limit` (défaut **25**, max API **100**). Affichage total + Précédent / Suivant. Pas de chargement de tout l’historique.

## Statistiques (cartes)

Données API uniquement :

- total (période)
- échecs
- warnings_errors
- permission_denied
- login_failure
- iam_changes

## Timeline & détail

- Timeline narrative (pas de `metadata_json` brut)
- Drawer détail : ids, dates locale + UTC, IP masquée, UA simplifié, métadonnées filtrées côté UI

## Fichiers principaux

- `pages/platform/ActivityCenterPage.tsx`
- `components/audit/*`
- `types/audit.ts`
- `services/auditApi.ts`
- styles dans `index.css` (bloc Activity Center)

## Limites actuelles

- Pas de purge / archivage depuis l’UI
- Pas de websocket
- Pas de tests unitaires frontend (projet sans stack)
- Pagination **offset/limit** (pas de cursor — décision étape 3)
- Export CSV uniquement depuis l’UI (JSONL disponible API)
- Rétention via CLI uniquement

## Export (étape 3)

Bouton **Exporter CSV** (platform admin / `security.audit.export`).  
Voir `docs/security/audit-export-security.md`.

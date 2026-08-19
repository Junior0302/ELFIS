# 01 — Audit couleurs runtime (AVANT / pendant BRAND.ELFIS.2)

## Surfaces auditées

| Surface | Constats principaux |
|---------|---------------------|
| `/home` | Navy shell OK ; accents verts KPI métier (autorisés Home hybride) |
| `/platform/organization` | Header générique ; lien « Admin → Équipe » legacy ; abonnement libellé ComptaPilot |
| `/platform/members` | **Invitation fond vert mint** ; avatar vert forêt ; rôles « Directeur financier / Comptable » ; titre « Admin · Équipe » |
| `/platform/relations` | CSS workspace ; peu de verts hardcodés |
| `/platform/documents` | Hub neutre relatif |
| `/platform/communications` | Neutre relatif |
| `/platform/settings` | Mixte |
| Drawer ELFIS | Navy gradient ; accent actif `#3d7eff` (proche mais ≠ blue-600 brief) |
| Sidebar plateforme | Gradient slate ; actif `#5b7cfa` |
| Launcher Espaces | Navy OK ; accents domaines discrets (BRAND.ELFIS.1) |

## Hardcodes Finance hérités (membres)

| Emplacement | Valeur | Action |
|-------------|--------|--------|
| `.member-invite` | `rgba(123, 196, 160, 0.1)` + border forêt | → surface / border ELFIS |
| `.member-avatar` | `#0b3d2e` → `#1f6b52` | → navy-950 / navy-900 |
| `ROLE_HELP` | factures / fiscalité | → descriptions transverses |
| `ROLE_LABELS_FR` | Directeur financier, Comptable | → Gestionnaire, Collaborateur (affichage) |
| PageHeader | Admin · Équipe | → ENTREPRISE / Membres et équipes |

## Tokens existants

- Theme Engine `--pilot-*` (elfis-core / comptapilot / salespilot)
- `PLATFORM_SURFACES` (unified-platform)
- Launcher `--launcher-navy: #0b1f3a`

**Décision :** consolider `--elfis-*` officiels + aliaser `--pilot-*` sous `.ps-shell--platform` / page membres. Ne pas dupliquer un 2e DS.

# 26 — Spatial runtime audit (AVANT UX.UNIFY.1.2)

Mesures dérivées du CSS / DOM runtime **avant** correction spatiale.
Captures manuelles Chris : viewport 1920 / 1440 / 1280 (colonne « mesuré » à compléter).

## Hypothèses de calcul

| Token / règle | Valeur AVANT |
|---------------|--------------|
| `--product-sidebar-expanded-width` | 240px |
| `--product-sidebar-collapsed-width` | 56px |
| Home `--ps-sidebar-w` (hybrid) | **190px** (divergence) |
| `--up-page-max-width` | `100rem` ≈ **1600px** |
| Frame `padding-inline` (pad-md) | `var(--space-4)` = **16px** |
| Frame `padding-block` | `var(--space-6)` = **24px** |
| `.ps-viewport` padding | **1.25rem (20px)** — **double** avec frame |
| Home legacy `.elfis-home--hybrid` | `max-width: 1480px` (neutralisé si `up-home--unified`) |
| `PlatformPageContainer` / `CONTAINER_SCALE.xl` | **1200px** (legacy, hors frame) |
| Sidebar Compta | gradient vert pâle `#e7f2ec` → `#f7faf8` |
| Sidebar Sales | `color-mix(pilot-secondary 70%, #fff)` bleu pâle |
| Sidebar Home | navy `#071426` |
| Chart hero FCC | `min-height: 16rem` + body `260–340px` |
| Chart half FCC | body `230–300px` |
| Template gap grid | token `5` = **20px** (pas 24 desktop) |

## Tableau largeurs AVANT (calculées)

| Viewport | Sidebar (exp.) | Main (viewport − sidebar) | Frame max effectif | Pad inline cumulé* | Contenu utile approx. |
|----------|----------------|---------------------------|--------------------|--------------------|------------------------|
| 1920 | 240 (Home 190) | 1680 (Home 1730) | min(1600, main−viewportPad) | 20+16+16 ≈ 52 | ~1548 (Home ~1480 legacy possible) |
| 1440 | 240 | 1200 | 1200−40 = 1160 | idem | ~1128 |
| 1280 | 240 | 1040 | 1040−40 = 1000 | idem | ~968 |

\*viewport pad 20 + frame 16×2 — **double container**.

| Écran | max-width page | Sidebar surface | Composition | Notes |
|-------|----------------|-----------------|-------------|-------|
| Home | 1600 frame / 1480 legacy | navy | header=hero ; main 8 (continuer+apps) ; aside 4 (activité+notif+statut) | Colonne centrale perçue étroite vs full bleed |
| Compta FCC | 1600 frame | **vert pâle** | sections verticales (analyser→essentiel→décider…) | Chart revenus trop haut si série faible |
| Sales | 1600 frame | **bleu pâle** | metrics + stack sections ; pas aside | 3e composition (pas 8/4 ciblé) |

## Mesures manuelles (Chris)

| Viewport | Écran | Sidebar px | Main px | Frame px | Margin auto L/R | Notes |
|----------|-------|------------|---------|----------|-----------------|-------|
| 1920 | Home | | | | | |
| 1920 | Compta | | | | | |
| 1920 | Sales | | | | | |
| 1440 | Home | | | | | |
| 1440 | Compta | | | | | |
| 1440 | Sales | | | | | |
| 1280 | Home | | | | | |
| 1280 | Compta | | | | | |
| 1280 | Sales | | | | | |

## Écarts vs contrat 1.2

1. max-width **1600 ≠ 1680**
2. pad inline desktop **16 ≠ 32**
3. sidebar Compta/Sales **≠ navy**
4. Home sidebar width **190 ≠ 240**
5. double padding viewport + frame
6. compositions Home/FCC/Sales non alignées sur squelette Header/Strip/KPI/Primary/Secondary/Ops/Activity
7. ChartCard sans clamp unifié 300–420 / hero 340–480
8. MetricCard sans `min-height: 132px`

## GO après correction

Voir [27-spatial-comparative.md](./27-spatial-comparative.md) + critères GO 14 points (doc 34).

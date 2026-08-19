# 27 — Spatial comparative (AVANT → APRÈS)

Mesures tokens + règles CSS. Captures manuelles Chris : colonnes « mesuré » (USM).

## Tokens

| Token | Avant | Après |
|-------|-------|-------|
| `--up-page-max-width` | 100rem ≈ 1600 | **1680px** |
| pad inline desktop | 16 | **32** |
| pad inline laptop ≤1440 | — | **24** |
| pad inline tablet ≤1024 | — | **20** |
| pad inline mobile ≤640 | — | **16** |
| pad block | 24 | **24–40** (clamp) |
| dashboard gap | 20 | **24 / 20 / 16** |
| sidebar surface | blanc / vert pâle / bleu pâle | **navy #071426** partout |
| Home `--ps-sidebar-w` | 190 | **240** (UI.P1) |
| viewport padding | 20 + frame | **0** (frame seul) |
| MetricCard min-h | — | **132px** |
| Chart body | FCC ad hoc 230–340 | **clamp 300–420** / hero **340–480** / weak ↓ |

## Largeurs calculées APRÈS (viewport 1920 / sidebar 240)

| Viewport | Main | Frame max | Pad inline | Contenu utile approx. |
|----------|------|-----------|------------|------------------------|
| 1920 | 1680 | 1680 | 32×2 | ~1616 |
| 1440 | 1200 | 1200 | 24×2 | ~1152 |
| 1280 | 1040 | 1040 | 24×2 | ~992 |

## Composition

| Slot | Home | Compta | Sales |
|------|------|--------|-------|
| Header | Tableau de bord | Tableau de bord | Tableau de bord |
| Strip | — | org/error | — |
| KPI | — | 12 | 12 |
| Primary | hero 8 + activité 4 | revenus 8 + priorités/alertes 4 | pipeline 8 + opp 4 |
| Secondary | continuer 8 + statut 4 | trésorerie 6 + CA 6 | activités 6 + tâches 6 |
| Operations | apps 8 + notif 4 | actions + health + traiter | quick actions |
| Recent | — | activité 8 + sync 4 | insights (+ generated_at) |

## Captures (Chris)

| ID | Viewport | Écran | Fichier | OK? |
|----|----------|-------|---------|-----|
| C01 | 1920 | Home | | |
| C02 | 1920 | Compta | | |
| C03 | 1920 | Sales | | |
| C04 | 1440 | Home | | |
| C05 | 1440 | Compta | | |
| C06 | 1440 | Sales | | |
| C07 | 1280 | ×3 | | |

# 09 — Wireframe Plan

**P1.1** · Écrans / frames à réaliser en **P1.2** (maquettes visuelles).  
Aucun développement dans P1.1 / P1.2 code — maquettes seulement en P1.2.

---

## Légende priorité

| Tag | Sens |
|-----|------|
| **P0** | Indispensable blueprint |
| **P1** | Important écosystème |
| **P2** | Nice-to-have première vague |

Format maquette : desktop 1440 · mobile 390 (frames clés).

---

## A — Auth & entrée

| ID | Écran | Priorité | Notes wireframe |
|----|-------|----------|-----------------|
| A1 | Landing ELFIS Core (hero) | P0 | Mark + phrase + CTA ; pas de cards hero |
| A2 | Login | P0 | Mark Core ; form centré |
| A3 | Post-login hub (aucun Pilot) | P0 | CTA launcher / grille |

---

## B — Platform Shell chrome

| ID | Écran | Priorité | Notes |
|----|-------|----------|-------|
| B1 | Shell + topbar (état Pilot actif) | P0 | Zones A–G doc 03 |
| B2 | Shell mobile topbar | P1 | Compact launcher / overflow |
| B3 | Banner erreur / offline | P2 | Sous topbar |

---

## C — App Launcher

| ID | Écran | Priorité | Notes |
|----|-------|----------|-------|
| C1 | Launcher ouvert (grille Pilot) | P0 | Mark teintés + noms |
| C2 | Launcher + filtre search | P1 | |
| C3 | Launcher récents | P1 | |
| C4 | Tuile Pilot disabled (no access) | P1 | |

---

## D — Global Search

| ID | Écran | Priorité | Notes |
|----|-------|----------|-------|
| D1 | Palette vide / suggestions | P0 | |
| D2 | Résultats groupés multi-Pilot | P0 | |
| D3 | Empty results | P1 | |
| D4 | Loading skeleton | P2 | |

---

## E — Notifications

| ID | Écran | Priorité | Notes |
|----|-------|----------|-------|
| E1 | Centre notifs (liste) | P0 | Filtres All / Platform / Pilot |
| E2 | Empty notifs | P1 | |
| E3 | Item severity warning/danger | P1 | |

---

## F — Profile & workspace

| ID | Écran | Priorité | Notes |
|----|-------|----------|-------|
| F1 | Menu profil ouvert | P0 | |
| F2 | Org switcher | P0 | |
| F3 | Page Profil | P1 | |
| F4 | Préférences | P1 | |
| F5 | Workspaces list | P1 | |

---

## G — Cross-product & Product Shell (contexte)

| ID | Écran | Priorité | Notes |
|----|-------|----------|-------|
| G1 | Product Shell ComptaPilot (chrome + sidebar fake) | P0 | Vert ; by ELFIS |
| G2 | Product Shell SalesPilot | P0 | Bleu ; **même** topbar layout |
| G3 | Switch Sales → Compta (avant/après pair) | P0 | Mark stable |
| G4 | Deep-link landing dans Pilot | P1 | |
| G5 | Hub « Choisir une app » | P0 | = A3 possible mutualisé |

Workspace métier détaillé (CRM board, ledger…) = **hors** P1.2 plateforme — placeholders grisés OK.

---

## H — États overlays

| ID | Frame | Priorité |
|----|-------|----------|
| H1 | Focus trap launcher | P1 |
| H2 | Esc / dismiss pattern | P2 |

---

## Ordre de réalisation P1.2 recommandé

```
1. A2 Login → B1 Shell
2. C1 Launcher → G1 / G2 Product shells
3. G3 Switch pair
4. D1–D2 Search
5. E1 Notifs
6. F1–F2 Profil / Org
7. A1 Landing + A3 Hub
8. Mobile B2 + subset C/D/E
```

---

## Inventaire total (P0)

```
A1 A2 A3
B1
C1
D1 D2
E1
F1 F2
G1 G2 G3 G5
─────────
≈ 14 frames P0 desktop
+ B2 mobile (P1)
```

---

## Hors wireframe P1.2

- Écrans métier Sales / Compta complets  
- Admin org deep  
- Marketing pages hors landing  
- Assets SVG logo final (Brand B0.6+)  

---

## Critère « P1.1 done »

- [x] Docs 01–08  
- [x] Plan 09  
- [ ] **P1.2** : maquettes des frames P0 ci-dessus  

**Arrêt P1.1.** Aucun développement. Suite = **P1.2 maquettes visuelles**.

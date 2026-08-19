# 04 — App Launcher

**P1.1** · Porte d’entrée de la famille Pilot.  
Composant **plateforme** — jamais gadget sidebar produit.

---

## Ouverture

```
Triggers:  [⊞] topbar  |  raccourci  |  empty-state hub
Motion:    180–240 ms panel ; pastilles stagger 30–50 ms
```

---

## Structure panel

```
┌─────────────────────────────────────┐
│ Applications              [Search]  │
├─────────────────────────────────────┤
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐        │
│ │Mark│ │Mark│ │Mark│ │Mark│        │
│ │vert│ │bleu│ │oran│ │navy│        │
│ Compta Sales  Doc   Core*          │
│ └────┘ └────┘ └────┘ └────┘        │
│ … HR Legal Marketing …             │
├─────────────────────────────────────┤
│ Récents                             │
│ · SalesPilot — Opportunités         │
│ · ComptaPilot — Écritures           │
└─────────────────────────────────────┘
```

\* Hub / settings plateforme si exposé comme tuile.

---

## Tuile Pilot

```
┌──────────────┐
│  [Mark teinté]│
│  NomPilot    │
│  sous-titre  │  ← mission 1 ligne (option)
└──────────────┘
     │
     ▼ clic
Product Shell du Pilot
+ fermeture launcher
+ primary theme Pilot
```

Règles Brand :

- **Même Mark**, teinte = primary Pilot  
- Wordmark CamelCase exact  
- Pas de second symbole métier  

---

## Comportements

| Action | Résultat |
|--------|----------|
| Clic Pilot disponible | Navigate + thème Pilot |
| Clic Pilot non provisionné | Empty / CTA admin (pas 404 silencieux) |
| Search in-launcher | Filtre tuiles + récents |
| Esc / clic outside | Ferme |
| Clavier | Flèches + Enter |

---

## Arbre

```
Launcher
├── Section Applications (tous Pilot org)
├── Section Récents (max 5)
├── Filter / search local
└── Footer lien (option) « Administration plateforme »
```

---

## Do / Don’t

```
DO                         DON’T
─────────────────────────  ──────────────────────────
Grille homogène            Tailles de tuiles chaos
Pastilles primary officielles  Dégradés / stickers
Récents utiles             Pubs / badges promo
```

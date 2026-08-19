# 05 — Global Search

**P1.1** · Recherche plateforme (palette ⌘K / Ctrl+K).

---

## Placement

```
Topbar zone D  →  bouton Search
Raccourci      →  ouvre palette centrée
```

```
            ┌─────────────────────────────┐
            │ 🔍 Rechercher dans ELFIS…   │
            ├─────────────────────────────┤
            │ Suggestions / résultats     │
            │ …                           │
            └─────────────────────────────┘
```

---

## Portée des résultats

```
Priorité
  1. Actions rapides (switch Pilot, ouvrir launcher…)
  2. Entités Pilot ACTIF
  3. Entités autres Pilot (groupées par app)
  4. Plateforme (membres, org settings, docs aide)
```

```
Résultats
├── Actions
├── ComptaPilot
│   ├── Facture F-204
│   └── Compte Client X
├── SalesPilot
│   └── Opportunité Acme
└── Plateforme
    └── Membre Alice
```

---

## Item résultat

```
[icône/Mark teinté]  Titre entité
                     Pilot · type · méta
```

Clic → deep-link (switch Pilot si besoin) + ferme palette.

---

## États

| État | UI |
|------|-----|
| Idle | Placeholder + raccourcis fréquents |
| Typing | Debounce ; skeleton lignes |
| Empty | « Aucun résultat » + lien launcher |
| Error | Message + retry |
| No permission | Entité masquée (pas d’erreur leak) |

---

## Hors scope P1.1 (noter)

- Recherche full-text documents lourds (DocPilot) = branche ultérieure  
- Command palette admin avancée = extension du même chrome  

---

## Do / Don’t

```
DO                        DON’T
────────────────────────  ────────────────────────
Grouper par Pilot         Liste plate illisible
Marquer le Pilot source   Résultats sans contexte
Clavier first             Souris only
```

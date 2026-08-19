# 03 — Architecture de marque

## Structure

```
Master Brand
└── ELFIS Core
    └── Product Brands (Pilot)
        ├── ComptaPilot
        ├── SalesPilot
        ├── DocPilot
        ├── HRPilot
        ├── LegalPilot
        ├── MarketingPilot
        ├── InventoryPilot
        ├── ProjectPilot
        ├── SupportPilot
        └── futurs Pilot
```

---

## Master Brand — ELFIS Core

**ELFIS Core** est la marque maître.

Elle porte :

- la plateforme ;
- l’identité publique (landing, login) ;
- le Platform Shell ;
- l’App Launcher ;
- la confiance, la sécurité, l’organisation.

Sur les surfaces publiques, la marque dominante est **ELFIS Core**, jamais un Pilot isolé.

---

## Product Brands — les Pilot

Chaque Pilot est une **marque produit** :

- nom propre (`ComptaPilot`, `SalesPilot`, …) ;
- couleur officielle ;
- mission et personnalité ;
- Product Shell (sidebar + navigation métier).

Un Pilot n’existe jamais « hors » d’ELFIS Core dans le discours officiel : il appartient à l’écosystème.

---

## Comment les logos sont reliés

Principe (à matérialiser en B0.2 / B0.3) :

```
[Pilot Mark]  +  [Wordmark produit]
                    └─ optionnel : by ELFIS Core
```

- Le **Pilot Mark** est commun.
- Le **wordmark** change selon la marque (ELFIS Core ou Pilot).
- La **couleur** d’accent suit la palette produit (ou navy pour la plateforme).

---

## Comment les noms sont utilisés

| Contexte | Forme recommandée |
|----------|-------------------|
| Titre de page publique | ELFIS Core |
| Shell produit | Nom du Pilot (ex. SalesPilot) |
| Sous-ligne shell | `by ELFIS Core` |
| App Launcher — carte | Nom du Pilot + courte description |
| Facturation / légal | ELFIS Core (plateforme) + produit concerné si besoin |
| Conversation orale | « ELFIS », « ComptaPilot », « SalesPilot » |

---

## « by ELFIS Core »

### Quand l’utiliser

- Header / sidebar d’un Product Shell
- Pages marketing d’un Pilot
- Documents commerciaux d’un Pilot
- Première mention d’un Pilot sur une surface mixte

### Quand ne pas l’utiliser

- Surfaces 100 % plateforme (landing ELFIS, login ELFIS) — le Master Brand suffit
- Répétition excessive dans la même vue (une fois suffit)
- Favicon / mark seule (trop petit)

### Forme

Toujours :

```text
SalesPilot
by ELFIS Core
```

ou en ligne :

```text
SalesPilot by ELFIS Core
```

Jamais : `by Elfis`, `by ELFISCORE`, `powered by ComptaPilot`.

---

## Quand utiliser seulement le nom du produit

Autorisé lorsque :

- l’utilisateur est **déjà** dans le Product Shell du Pilot ;
- le contexte plateforme est visible ailleurs (topbar, launcher) ;
- l’espace est trop restreint pour le lockup complet.

Exemple : onglet navigateur `SalesPilot — Pipeline` (la topbar rappelle ELFIS).

---

## Hiérarchie visuelle recommandée

1. **Surfaces publiques** — ELFIS Core dominant.
2. **Platform Shell** — ELFIS + launcher ; le produit actif est secondaire mais clair.
3. **Product Shell** — Pilot dominant ; ELFIS en signature (`by ELFIS Core`).

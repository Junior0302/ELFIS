# 09 — Principes de design (UX plateforme)

**ELFIS Platform Blueprint V1**

---

## Objectif UX

> L’utilisateur doit ressentir **un seul logiciel** — ELFIS — même en changeant de Pilot.

Pas une collection d’apps disparates. Pas une sensation « je me reconnecte à un autre outil ».

---

## Une seule plateforme

| Élément | Appartenance | Comportement |
|---------|--------------|--------------|
| Topbar / Mark ELFIS | Core | Toujours présent |
| App Launcher | Core | Change de Pilot sans rupture d’identité |
| Recherche globale | Core | Cross-Pilot quand disponible |
| Notifications | Core | Centre unifié |
| Org / profil | Core | Persistent |
| Sidebar / workspace | Pilot actif | Expertise métier |

Alignement : [`../platform/01-experience-principles.md`](../platform/01-experience-principles.md) · [`../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md`](../brand/ELFIS-Brand-Book-v1/07-platform-vs-product.md)

---

## Design System

- Une **source de vérité visuelle** (tokens, composants gouvernance).
- Les Pilots varient par **accent / wordmark**, pas par un nouveau langage UI.
- Interdit : inventer une UI parallèle hors Design System pour « aller plus vite ».

Docs Design System / brand : `frontend/docs/design-system-*.md` · Brand Book.

---

## Navigation

1. **Plateforme d’abord** — chrome ELFIS stable.
2. **Un Pilot à la fois** — Product Shell clair.
3. **Bascule prévisible** — launcher + raccourcis ; < quelques clics entre Compta et Sales.
4. **Deep-links** — depuis notifs, Aura, widgets, vers la vérité chez l’owner.

---

## Widget Framework

Les tableaux de bord et surfaces « command center » s’appuient sur une **coquille produit-agnostique** :

- états loading / ready / empty / error ;
- variants (compact, chart, list, hero, score…) ;
- pas de couleurs métier imposées par le framework.

Référence engagée : [`../comptapilot/financial-command-center/04-widget-framework.md`](../comptapilot/financial-command-center/04-widget-framework.md)  
Consommateur V1 : Financial Command Center (ComptaPilot). Extension future : autres Pilots.

Règle Blueprint : un widget **affiche** une capacité / métrique ; il **n’invente pas** un second owner de donnée.

---

## Raccourcis

| Intention | Pattern |
|-----------|---------|
| Recherche / actions | Palette (⌘K / Ctrl+K) |
| Changer de Pilot | Launcher |
| Aller à l’entité owner | Deep-link, pas copie d’écran |
| Aide contextuelle | Aura / aide plateforme |

---

## Do / Don’t (rappel)

```
DO                              DON’T
─────────────────────────────   ─────────────────────────────
Une sensation ELFIS             5 looks d’apps différentes
Chrome stable                   Re-login à chaque Pilot
Widgets via framework           Cards métier hors contrat
Attribution de source           Données « anonymes » sans owner
```

---

## Synthèse

> **Design System + shell + widgets + raccourcis** = une plateforme.  
> Les Pilots apportent l’expertise, pas une nouvelle identité visuelle totale.

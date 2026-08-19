# 07 — Platform vs Product

## Distinction officielle

| | **Platform Shell** | **Product Shell** |
|--|--------------------|-------------------|
| **Marque** | ELFIS Core | Pilot actif |
| **Rôle** | Cadre commun | Espace métier |
| **Couleur dominante** | Bleu nuit ELFIS + surfaces neutres | Primary du Pilot |
| **Navigation** | Transverse | Métier du Pilot |

---

## Platform Shell — toujours présent

Le Platform Shell porte les éléments **transverses** :

| Élément | Rôle |
|---------|------|
| **Logo / Mark ELFIS** | Identité plateforme |
| **App Launcher** | Changer de Pilot |
| **Recherche** | Recherche globale (quand disponible) |
| **Organisation** | Contexte multi-org |
| **Notifications** | Alertes plateforme |
| **Profil** | Compte, déconnexion |

Le Platform Shell **n’appartient pas** à ComptaPilot ni à SalesPilot.  
Il appartient à **ELFIS Core**.

L’App Launcher est un composant **plateforme**, jamais un gadget de sidebar produit.

---

## Product Shell — spécifique au Pilot

Le Product Shell porte l’expertise :

| Élément | Rôle |
|---------|------|
| **Logo / lockup produit** | Ex. SalesPilot + `by ELFIS Core` |
| **Sidebar** | Navigation métier |
| **Accent couleur** | Primary du Pilot |
| **Workspace** | Contenu métier (listes, boards, détails) |

Exemples :

- Product Shell ComptaPilot → vert, nav finance
- Product Shell SalesPilot → bleu, nav CRM

---

## Composition recommandée

```
┌─────────────────────────────────────────────┐
│  PLATFORM SHELL (topbar ELFIS)              │
│  Mark · Launcher · Org · Notif · Profil     │
├──────────────┬──────────────────────────────┤
│ PRODUCT      │  WORKSPACE                   │
│ SHELL        │  contenu métier              │
│ (sidebar)    │                              │
└──────────────┴──────────────────────────────┘
```

---

## Surfaces publiques

Landing et Login **ne sont pas** des Product Shells.

Ce sont des surfaces **ELFIS Core** (Master Brand) :

- pas de sidebar ComptaPilot ;
- pas de promesse exclusivement finance ;
- identité navy plateforme.

---

## Interdictions

- Faire croire que l’App Launcher est « dans » ComptaPilot.
- Appliquer le vert Compta sur toute la plateforme.
- Masquer ELFIS Core derrière un seul Pilot sur les pages publiques.
- Dupliquer profil / org / launcher uniquement dans la sidebar produit sans topbar plateforme.

---

## Lien avec le Design System

Le Design System implémente cette séparation (tokens `--pilot-*`, `data-product`, layouts).  
Le Brand Book **décide** ; le Design System **applique** (phases B0.6 / B0.7).

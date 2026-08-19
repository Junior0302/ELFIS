# 05 — Palette officielle

## Statut

Cette palette est **figée au niveau Brand Book**.

Son **application technique** (Design System, CSS, écrans) relève des phases ultérieures (B0.4+).  
B0.1 ne modifie aucun token runtime.

---

## Couleurs primaires produit

| Marque | Famille | Primary (référence) | HEX de référence |
|--------|---------|---------------------|------------------|
| **ELFIS Core** | Bleu nuit | Navy premium | `#0B1F3A` |
| **ComptaPilot** | Vert | Émeraude finance | `#0B3D2E` |
| **SalesPilot** | Bleu | Bleu professionnel | `#1D4ED8` |
| **DocPilot** | Orange | Orange documentaire | `#C2410C` |
| **HRPilot** | Violet | Violet équipes | `#6D28D9` |
| **LegalPilot** | Bordeaux | Bordeaux juridique | `#7F1D1D` |
| **MarketingPilot** | Rose | Rose / magenta maîtrisé | `#BE185D` |
| **InventoryPilot** | Turquoise | Cyan / turquoise stocks | `#0E7490` |
| **ProjectPilot** | Turquoise profond | Teal projets | `#0F766E` |
| **SupportPilot** | Indigo | Indigo service | `#3730A3` |

> **Note Brand :** DocPilot est officiellement **orange** dans ce Brand Book.  
> Toute divergence historique dans le Design System sera alignée lors de l’application visuelle (pas en B0.1).

---

## Secondaires & accents (par marque)

### ELFIS Core

| Rôle | HEX | Usage |
|------|-----|--------|
| Primary | `#0B1F3A` | Shell plateforme, titres forts |
| Secondary | `#E8EEF6` | Surfaces légères |
| Accent | `#3D7EFF` | Liens, focus, CTA plateforme |

### ComptaPilot

| Rôle | HEX | Usage |
|------|-----|--------|
| Primary | `#0B3D2E` | Sidebar, CTA finance |
| Secondary | `#E7F2EC` | Surfaces |
| Accent | `#7BC4A0` | Mentions, focus doux |

### SalesPilot

| Rôle | HEX | Usage |
|------|-----|--------|
| Primary | `#1D4ED8` | Sidebar, CTA sales |
| Secondary | `#E8F0FE` | Surfaces |
| Accent | `#60A5FA` | Focus, highlights |

### DocPilot

| Rôle | HEX | Usage |
|------|-----|--------|
| Primary | `#C2410C` | Identité Doc |
| Secondary | `#FFF7ED` | Surfaces |
| Accent | `#FB923C` | Focus |

### Autres Pilot

Chaque Pilot suit le même schéma : **primary** (identité) · **secondary** (surface teintée) · **accent** (interaction).

Les valeurs détaillées pour HR / Legal / Marketing / Inventory / Project / Support seront reprises du Design System au moment de l’implémentation, sous réserve d’alignement avec ce tableau.

---

## Couleurs système (globales)

Partagées par toute la plateforme — **ne changent pas** selon le Pilot actif.

| Rôle | Intention | HEX de référence |
|------|-----------|------------------|
| **Success** | Validation, succès | `#15803D` |
| **Warning** | Attention, risque maîtrisé | `#C4782B` |
| **Danger** | Erreur, destructif | `#B42318` |
| **Info** | Information neutre | `#3D7EFF` |
| **Neutral 900** | Texte principal | `#10241C` / ink sombre |
| **Neutral 600** | Texte secondaire | `#5C6B64` |
| **Neutral 200** | Bordures | `#E6DFD0` / line |
| **Neutral 0** | Fond blanc | `#FFFFFF` |

Les couleurs système ne remplacent jamais la primary produit pour la sidebar ou le branding.

---

## Règles d’usage

1. **Un Pilot = une primary dominante** dans son Product Shell.
2. **La plateforme = navy ELFIS** sur landing, login, Platform Shell.
3. **Interdiction** d’utiliser le vert ComptaPilot sur SalesPilot (et inversement).
4. **Les accents** servent aux interactions, pas à redéfinir l’identité.
5. **Contraste** : texte sur primary doit rester accessible (WCAG AA minimum).

---

## Ce que B0.1 ne fait pas

- Aucune mise à jour de `palettes.ts`
- Aucune modification de CSS
- Aucune capture d’écran mise à jour

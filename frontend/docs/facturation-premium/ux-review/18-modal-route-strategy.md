# 18 — Stratégie route modale Composer

## Pattern retenu : nested modal route

Documents reste le parent React Router ; le Composer est une **surface modale** synchronisée à l’URL.

| URL | UI | Notes |
|-----|-----|-------|
| `/facturation/documents` | Liste Documents | Entrée normale |
| `/facturation/documents?create=1` | Documents + STATE 1 (type) | Deep link pop-in |
| `/facturation/documents/new?type=facture\|devis\|avoir` | Documents (monté) + STATE 2 (ComposerDialog) | Création / refresh / historique |
| `/facturation/nouveau?type=…` | **Redirect** → `/facturation/documents/new?type=…` | Compat legacy / favoris |

### Pourquoi nested (plutôt que backgroundLocation seul)

- Parent `documents` **ne se démonte pas** quand on passe à `documents/new`.
- Pas besoin de dupliquer `location.state.backgroundLocation` pour le cas nominal.
- Deep link / refresh sur `/documents/new` : React Router monte Documents (parent) puis la phase composer — arrière-plan réel, pas page cassée.
- Retour / fermeture : `navigate('/facturation/documents')` ou `?doc=` / `?create=1` ; focus restauré sur « Créer un document ».

### Background location (alternative documentée)

Pattern RR classique (`state.backgroundLocation`) reste valide si un jour Composer s’ouvre depuis une autre liste. Non requis tant que Composer est enfant de Documents.

## Transitions d’état

```
STATE 1 (type, dialog sm)
  └─ Créer le document
       → navigate /documents/new?type=…  (même overlay, phase=composer)
STATE 2 (ComposerDialog large)
  └─ Fermer / Revenir Documents
       → /facturation/documents[+?doc=]
  └─ Créer un autre
       → /facturation/documents?create=1  (STATE 1)
```

Pas de navigation visuelle vers une page Composer indépendante. Le chrome Documents (sidebar, nav Facturation) reste derrière l’overlay (inert + scroll lock).

## Deep link sans session Documents préalable

Ouvrir `/facturation/documents/new?type=facture` :
1. Monte `FacturationDocumentsPage` (arrière-plan).
2. Ouvre ComposerDialog plein workflow.
3. Fermer → `/facturation/documents`.

Sans `type` sur `/new` → redirect `/facturation/documents?create=1`.

## Shell Full Focus (F1.3.1.1)

`isComposerFullFocusPath` ne s’applique plus au flux nominal (plus de page `/nouveau` visible). Le Focus UX est **dans** le modal (header ComposerFocusLayout), pas un viewport shell sans sidebar.

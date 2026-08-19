# 12 — Composer Focus Layout

## Structure (F1.3.1.2)

```
Documents (monté)
  └─ ComposerDialog (modal)
       └─ ComposerFocusLayout
            ├─ FocusHeader (retour | type+titre+statut | autosave+issues | actions)
            ├─ Progress légère
            ├─ Workspace (Editor ~65% | Preview ~35%)
            ├─ Confirmation post-création (si besoin)
            └─ Footer optionnel
```

En tests / mode `presentation="page"`, le même layout peut rendre hors dialog.

## Composant

`composer-framework/ComposerFocusLayout.tsx` — réutilise `ComposerStatus`, `ComposerProgress`, `ComposerActions`, `ComposerBody`, `ComposerPreview` (slot).

Attributs : `data-composer-full-focus="true"`, `data-focus-mode="true"` ; en modal : `elf-cmp-focus--modal`.

## Header

| Zone | Contenu |
|------|---------|
| Gauche | ← Documents, titre, type, statut |
| Centre | Autosave, « N points à vérifier » |
| Droite | ≤ 2 secondaires + 1 primaire |

## Workspace

- Éditeur scroll indépendant ; sections en surfaces blanches.
- Preview sticky / pleine hauteur panneau ; moteurs PDF inchangés.
- Dans le dialog : hauteur = corps modal (pas `100vh - topbar`).

## Confirmation

Après 1er enregistrement ou envoi : Ouvrir / Envoyer / Revenir aux Documents / Créer un autre — **dans** le modal.

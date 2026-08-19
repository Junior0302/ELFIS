# 13 — Focus / Modal Routing

## Route nominale (F1.3.1.2)

`/facturation/documents/new?type=facture|devis|avoir`

Documents (parent) reste monté ; Composer = modal (`DocumentCreateFlow` + `ComposerDialog`).

Sans `type` sur `/new` → redirect `/facturation/documents?create=1`.

## Compat

`/facturation/nouveau?type=…` → redirect `/facturation/documents/new?type=…`.

## Shell

`isComposerFullFocusPath` → **false** (plus de page Focus qui masque sidebar).  
`isComposerModalPath` détecte `/documents/new`.

Chrome Documents (nav Facturation, sidebar) reste derrière l’overlay (inert).

## Persistance

Autosave, pickers, PDF : restent sur `/documents/new` → modal inchangé.

## Sorties

| Action | Destination |
|--------|-------------|
| ← Documents / Annuler / close | `/facturation/documents` (+ `?doc=` si créé) |
| Confirm dirty | Dialog 3 actions puis Documents |
| Ouvrir le document | `/facturation/documents?doc=` |
| Créer un autre | `/facturation/documents?create=1` |
| Revenir aux Documents | `/facturation/documents` (+ refresh liste) |

Voir aussi [18-modal-route-strategy.md](./18-modal-route-strategy.md).

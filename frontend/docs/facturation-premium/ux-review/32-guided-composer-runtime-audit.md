# 32 — Guided Composer Runtime Audit (F1.3.2)

## Contexte

F1.3.1.3 a stabilisé le **root modal** (`DocumentCreationModalRoot` + `ComposerModalStage`).  
Le contenu du Composer affichait encore **toutes les sections freeform** d’un coup → formulaire long.

## Inventaire runtime (avant F1.3.2)

| Zone | Fichier | Comportement | Action F1.3.2 |
|------|---------|--------------|---------------|
| Modal root / overlay | `ComposerDialog.tsx`, `DocumentCreateFlow.tsx` | Persistant, `closeOnRouteChange:false` | **Ne pas modifier** |
| `ComposerModalStage` | `composerModalMachine.ts` | closed→type→composer→confirmation | **Inchangé conceptuellement** |
| Contenu éditeur | `FacturationComposerPage` `freeformBody` | Client + Lignes + Conditions + Notes + Paiement + Totaux + Contrôles empilés | **Une étape à la fois** |
| Progression | `deriveProgress` + `COMPOSER_PROGRESS_STEPS` (type/client/lines/…) | Indicateur dérivé du draft, pas de navigation | Remplacer (modal) par **6 `ComposerStep`** |
| PDF / Live preview | `previewSlot` sticky droite | Monté en continu | **Conserver** ; ne pas démonter entre étapes |
| Pickers | `CustomerPicker`, `ProductPicker` | Closed-by-default | **Conserver** |
| Validation | `deriveWizardControls` + insights | Affichée en bas freeform | Étape **review** (dédup) |
| Autosave / draft | même `FacturationWizardDraft` | Unique | **Conserver** — pas de nouveau draft system |
| Actions header | Annuler / Enregistrer / Envoi | Toujours visibles | Finalization = actions réelles ; footer Retour/Continuer |

## Séparation des machines

```
ComposerModalStage  = surface overlay (inchangé)
ComposerStep        = parcours guidé dans stage "composer"
```

## Hors scope

Root modal, Overlay Manager, calculs, APIs, moteur PDF, Vault, mailer, Billing, F1.4.

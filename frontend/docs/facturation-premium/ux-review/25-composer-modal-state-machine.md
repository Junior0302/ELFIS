# 25 — State machine Composer modal (F1.3.1.3)

## Source unique

`ComposerModalStage = "closed" | "type_selection" | "composer" | "confirmation"`

Fichier : `workflow/composerModalMachine.ts` + orchestration `DocumentCreateFlow.tsx`.

## Transitions

```
closed → type_selection → composer → confirmation | closed
confirmation → closed | composer
type_selection → closed
```

## Mapping UI

| Stage | Overlay | Contenu |
|-------|---------|---------|
| closed | absent | — |
| type_selection | sm | radios type + Créer |
| composer | large | FacturationComposerPage modal |
| confirmation | large | même Composer + bandeau post-création |

Pas de booléens concurrents `typeOpen` + `bridgeComposer` + `composerMatch` comme vérité — URL et `typeOpen` parent **hydratent** la machine uniquement.

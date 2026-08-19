# 13 — Aura migration

## Architecture

```
Aura globale (/platform/aura)
  └── réutilise CopilotePage / aiAssistantApi

Assistant financier (/copilote)
  └── même moteur, contexte ComptaPilot + lien « Ouvrir Aura »
```

## Décisions

- Pas de nouvelle IA
- Pas d’agent autonome
- Financial Engine non déplacé
- Libellé Compta : « Assistant financier » (plus « AI Financial Assistant » global)

## Dette S1.2

- Contexte Aura cross-Pilot dédié
- Suggestions plateforme (nav, synthèse) distinctes du copilote finance

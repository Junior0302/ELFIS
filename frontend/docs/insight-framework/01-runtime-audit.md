# 01 — Runtime audit (messaging / insights)

**Phase F1.2.5** · Lecture seule des surfaces existantes avant unification présentation.

## Surfaces auditées

| Surface | Emplacement | Shape / taxonomie | UI actuelle |
|---------|-------------|-------------------|-------------|
| **FCC — Alertes** | `financial-command-center/`, `FinancialAlert` | `info \| warning \| critical` | Liste dense + `WidgetBadge`, labels FR via `severityLabel` |
| **FCC — Priorités** | `priorities.ts` → `DayPriority` | `critical \| high \| normal \| info` | Badge anglais + Link CTA |
| **FCC — Health** | `HealthScore` + `recommendations[]` | score / grade / message / tips string | Gauge + listes ad hoc |
| **Document Composer** | `ComposerValidationIssue` | `info \| warning \| error \| suggestion` | Liste bordure locale, sévérité en texte brut |
| **Wizard controls** | `WizardValidationIssue` | `info \| warning \| error` (⊆ composer) | Mappé vers Composer |
| **System Health** | `SystemAlert` | `info \| warning \| critical` | Cards impact / reco |
| **Toasts** | `ui/Toast.tsx` | `info \| success \| error` | Auto-dismiss 4,5 s |
| **Notifications** | `AppNotification` | `info\|success\|warning\|error\|critical` | Bell + page |
| **Assistant** | `StructuredAnswer` | confidence + recommendations | Chat (hors scope UI Insight V1) |
| **Overlays DS** | `ConfirmTone` | `neutral\|warning\|danger` | Dialogs (stack UI ≠ priorité métier) |

## Duplications identifiées

| Concept | Divergence |
|---------|------------|
| Sévérité | 4+ grilles incompatibles (finance, composer, toast, notif) |
| Priorité | `PriorityLevel` métier vs `OverlayPriority` stack UI |
| Labels | FR (`Critique` / `Vigilance`) vs tokens EN (`critical` / `high`) côte à côte dans FCC |
| Couleurs | `--pilot-*` DS vs hex locaux Composer vs hardcode WidgetBadge |
| CTA | Link FCC, texte `action` inline alertes, boutons toast, `ProposedAction` assistant |
| Confiance / source | Assistant affiche confiance ; FCC / Composer n’ont pas de pattern unifié — **ne pas inventer** |

## Décisions F1.2.5

1. **Insight Framework** = couche présentation Core ; ownership données inchangé.
2. Mapping **1:1** depuis shapes existantes ; fallback `null` / liste vide si impossible.
3. Confiance & source **affichées seulement si fournies**.
4. Pas de duplication Widget Framework : Widgets restent containers ; Insights rendent le contenu signal.
5. Aura / moteurs / API / calculs **non modifiés**.
6. F1.3 **non démarré**.

## Non-objectifs audit

- Unifier backend notifications / toast global
- Brancher Assistant chat sur Insight UI (hors phase)
- Remplacer System Health page entière

# 06 — Validation

Réutilise `deriveWizardControls(draft)` F1.0.

Sévérités Composer : `info` | `warning` | `error` | `suggestion` (suggestion prête UI ; F1.0 émet info/warning/error).

Ne bloque pas inutilement la navigation (même règles `canLeaveFacturationStep`).

Autosave UI : `Enregistrement…` / `Enregistré il y a Xs` / `Erreur` + Réessayer — sur `createSalesDoc` / `updateSalesDoc` existants (update auto uniquement si brouillon déjà créé).

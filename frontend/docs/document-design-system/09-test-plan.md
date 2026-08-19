# 09 — Plan de tests

## Automatisés (DDS01–DDS40)

| ID | Cas | Couverture |
|----|-----|------------|
| DDS01–04 | resolveShowLogoDefault | FE unit |
| DDS05–07 | PDF-safe / hasLogo | FE unit |
| DDS08–10 | render config, labels, couleurs | FE unit |
| DDS11–15 | branding_json / org pref / showLogo PDF | BE `test_document_design_system.py` |
| DDS16–18 | pas de `draft` / ComptaPilot dans PDF | BE |
| DDS19–22 | métadonnées devis / avoir / facture | BE |
| DDS23–25 | footer légal données réelles | BE existant + DDS |
| DDS26–30 | create/update branding API | smoke via billing |
| DDS31–35 | StudioLivingPdf délègue DDS | FE guided smoke |
| DDS36–40 | permissions / template premium_v1 | doc + code review |

## Manuels — À tester manuellement (DP01–DP25)

| ID | Scénario |
|----|----------|
| DP01 | Vérification : segment Avec/Sans logo live |
| DP02 | Sans logo → nom fort, pas de trou layout |
| DP03 | Avec logo + fichier PNG → logo preview + PDF |
| DP04 | Sans logo org → message + Continuer sans logo |
| DP05 | Ajouter logo (sous-dialog) → Avec logo + draft intact |
| DP06 | SVG upload → preview HTML ; PDF = thumb ou nom |
| DP07 | Case défaut cochée → prochains docs héritent |
| DP08 | Case défaut **décochée** → pas d’écriture org |
| DP09 | User sans settings.manage : pas d’upload logo |
| DP10 | User edit doc : peut toggle showLogo |
| DP11 | Download PDF = même showLogo que draft |
| DP12 | Email joint = même branding |
| DP13 | Vault archive = même PDF |
| DP14 | Facture : Facturé à + échéance |
| DP15 | Devis : Destinataire + validité |
| DP16 | Avoir : Crédit pour |
| DP17 | Multipage : Page N footer |
| DP18 | Impression N&B lisible |
| DP19 | Pas de « draft » visible PDF client |
| DP20 | Mentions légales = org only |
| DP21 | Couleurs org discrètes |
| DP22 | Autosave persiste branding_json |
| DP23 | Live ↔ PDF structure cohérente |
| DP24 | Modal Composer ne quitte pas pour logo |
| DP25 | Régression totaux / calculs inchangés |

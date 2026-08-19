# A1.1.3 / A1.1.2 — Encodage mailto (Outlook « + »)

Date : 2026-08-01  
Périmètre : Facturation → compositeur e-mail mode messagerie personnelle  
Lié à : `09-email-composer-state-loss-remediation.md`

## Cause

`buildMailtoUrl` construisait la query avec `URLSearchParams` / `application/x-www-form-urlencoded`, qui encode les espaces en `+`.  
Outlook et plusieurs clients affichent le `+` littéral dans l’objet et le corps (`Facture+FAC-2026-0001+—+Crealab+Auto`).

Cause secondaire UX : le corps client contenait une note technique (« le mailto ne peut pas… ») et `window.location.href = mailto:` pouvait provoquer focus / effets de navigation ressentis comme un reset.

## Correctif

| Point | Avant | Après |
|-------|-------|-------|
| Encodage | `URLSearchParams` → `+` | `encodeURIComponent` par valeur → `%20` |
| Newlines | `\n` brut | normalisés CRLF `\r\n` avant encode |
| Ouverture | `window.location.href` | `<a>` click (`openMailtoUrl`) |
| Corps client | jargon mailto | « Le PDF … a été téléchargé. Ajoutez-le… » |
| Note technique | dans le body client | uniquement UI ELFIS |
| Confirmation | checkbox seule | + `ConfirmDialog` avant ouverture |
| Nom PDF | souvent `FAC-….pdf` (Content-Disposition) | override `Facture-{number}-{org}.pdf` |

Fichiers : `frontend/src/mailtoComposer.ts`, `mailtoComposer.test.ts`, `SalesDocPreviewModal.tsx`, `api.ts` (`preferredFilename`).

## Tests

- Vitest : espaces, accents, `€`, apostrophe, tiret long, pas de `+`, CRLF, soft « pièce jointe », filename
- Pas de régression `emailComposerDraft` / `productPhase` (état compositeur)

## GO / NO GO

**GO technique** encodage + confirmation après vitest / tsc / build.  
**NO GO commercial** tant que Chris n’a pas validé l’ouverture Outlook manuelle (objet sans `+`, PDF nommé clairement).

# A1.1.2 — Perte d’état du compositeur e-mail & reset navigation

Date : 2026-08-01  
Périmètre : Facturation → Aperçu → Envoi (pas A1.2, pas SalesPilot / Home / Launcher / Command Center)

## Cause racine

**Trigger :** `window` `focus` → `SubscriptionProvider.refresh()` → `setLoading(true)`  
**Effet :** `ProductAccessLayout` calcule `resolveProductPhase(..., { subscriptionLoading: true })` → `phase === 'loading'`  
**Conséquence :** démontage complet de `WorkspaceLayout` / `FacturationPage` / `SalesDocPreviewModal` → perte du formulaire (sensation de « refresh » sans `location.reload`).

Cause secondaire (si le modal restait monté) : `useEffect` du compositeur dépendait de `doc.customer_email` et réappliquait `salesDocEmails` preview → reset des champs + onglet Actions → Aperçu.

## Reproduction (timeline)

| Timestamp | Route | Document ID | Overlay open | Composer mounted | Form state | Trigger | Unmounted | Cause |
|-----------|-------|-------------|--------------|------------------|------------|---------|-----------|-------|
| t0 | `/facturation` | N | oui | oui | vierge | Ouvrir aperçu | — | — |
| t1 | idem | N | oui | oui | dirty (dest/objet/corps) | Saisie | — | état local |
| t2 | idem | — | **non** | **non** | **perdu** | Changement d’onglet / focus fenêtre | `FacturationPage` + modal | `subscriptionLoading` → phase loading |
| t3 | `/facturation` | — | non | non | vide | Refresh abo terminé | remount page | `previewDoc === null` |

Preuve code : `subscriptionContext.tsx` (focus → refresh + loading), `productPhase.ts` (loading gate), `ProductAccessLayout.tsx`.

## Composant fautif

| Source | Trigger | Effet sur composer | Autorisé / Interdit | Correctif |
|--------|---------|-------------------|---------------------|-----------|
| `SubscriptionProvider` focus refresh | `window` focus | `loading=true` → unmount workspace | Interdit (gate loading sur refresh) | Refresh silencieux si abo déjà connu |
| `resolveProductPhase` | `subscriptionLoading` | phase loading même avec abo | Interdit | loading seulement si `subscription == null` |
| `ProductAccessLayout` | `loading` | remplace Outlet par « Chargement… » | Interdit en refresh | `loading && subscription == null` |
| `SalesDocPreviewModal` useEffect | `doc.customer_email` / meta | reset form + tab | Interdit si dirty | init une fois / doc + garde draft |
| Overlay dismiss | Escape / backdrop | fermeture silencieuse | Interdit si dirty | confirm Continuer / Abandonner |
| Sync notifications 30s | poll | re-render SyncProvider | OK (ne ferme pas) | inchangé |
| `onSent` + `load()` | succès / échec | update `previewDoc` | OK si pas reset form | garde `formInitializedRef` |

## Correctifs

1. **Focus refresh silencieux** — `subscriptionContext` : `setLoading(true)` uniquement si aucun abonnement en mémoire.
2. **Gate produit** — `resolveProductPhase` + `ProductAccessLayout` : ne pas repasser en `loading` quand un abonnement est déjà résolu.
3. **Compositeur protégé** — `SalesDocPreviewModal` :
   - init formulaire une fois par `doc.id` (`formInitializedRef`) ;
   - pas de reset sur refresh meta / churn d’objet `SalesDoc` ;
   - dirty tracking ; fermeture X / Escape / backdrop / Annuler / Modifier / Marquer payée → confirm si dirty ;
   - échec d’envoi : conserve champs + erreur + Retry ; succès : clear draft + baseline ;
   - lock double-clic inchangé ; libellé « Envoi en cours… ».
4. **Brouillon session** — clé `elfis.email-draft.{organizationId}.{documentId}` (sessionStorage) : recipient/cc/bcc/subject/message/sendMode/acks/timestamp ; TTL 12h ; pas de tokens / Brevo / PDF ; autosave debounce 400 ms ; clear succès / abandon.

## Stratégie draft

- Stockage : **sessionStorage** (isolé onglet, pas de fuite cross-session longue).
- Restore à la réouverture du même org+doc.
- Clear : envoi OK, abandon confirmé.

## Comportement refresh

- Refresh abo focus : **ne démonte plus** la surface facturation.
- Refresh meta e-mail / PDF : met à jour logs / PDF / flags mailer **sans** écraser le brouillon local.
- Pas de désactivation globale Sync / notifications.

## Erreur / succès

| Cas | Fenêtre | Champs | Draft | UI |
|-----|---------|--------|-------|-----|
| Erreur Brevo/SMTP / throw | reste ouverte | conservés | conservé | erreur + Retry |
| Succès serveur | reste ouverte (UX actuel) | baseline reset | clear | hint succès |
| Mailto OK | reste (après mailto) | baseline | clear | hint mailto |

## Dette

- Confirm abandon non branché sur logout / org switch (hooks Overlay `closeAll` force encore) — hors parcours facturation courant.
- Logs `[EmailComposer]` DEV : réduire encore si bruit excessif après validation Chris.
- Credentials Brevo réels toujours côté ops (A1.1.1).
- Encodage mailto / confirmation Outlook : voir `10-mailto-encoding-remediation.md` (A1.1.2 suite).

## GO / NO GO

**GO technique** après tsc + build + tests unitaires ci-dessous.  
**NO GO commercial final** tant que Chris n’a pas validé M01–M20 manuellement.

---

## TABLEAU A — Tests Cursor (1–30)

| # | Test | Résultat | Preuve | Fichier | Commentaire |
|---|------|----------|--------|---------|-------------|
| 1 | Repro focus → loading gate | OK code | phase loading avec abo | `productPhase.ts` | Cause confirmée |
| 2 | `resolveProductPhase` garde entitled | OK | vitest | `productPhase.test.ts` | focus refresh |
| 3 | ProductAccessLayout gate | OK code | `loading && !subscription` | `ProductAccessLayout.tsx` | défense en profondeur |
| 4 | Subscription silent refresh | OK code | `gateLoading` | `subscriptionContext.tsx` | pas de setLoading si abo |
| 5 | Init form une fois / doc | OK code | `formInitializedRef` | `SalesDocPreviewModal.tsx` | — |
| 6 | Pas de dep `customer_email` | OK | deps `[doc.id,token,orgId]` | modal | cause secondaire |
| 7 | Dirty → confirm abandon | OK code | `ConfirmDialog` | modal | Continuer / Abandonner |
| 8 | Escape dirty bloque OverlayManager | OK | `dismissible={!dirty}` | modal | + Escape custom |
| 9 | Draft write/read/TTL/clear | OK | vitest | `emailComposerDraft.test.ts` | sessionStorage |
| 10 | Clé isolée org/doc | OK | vitest | idem | — |
| 11 | Pas de secrets dans draft | OK | vitest | idem | — |
| 12 | Autosave debounce | OK code | 400 ms | modal | — |
| 13 | Restore à réouverture | OK code | `readEmailComposerDraft` | modal | — |
| 14 | Clear draft succès | OK code | `clearEmailComposerDraft` | modal | — |
| 15 | Erreur conserve champs | OK code | catch sans clear | modal | — |
| 16 | Double-clic lock | OK code | `sendingLock` | modal | inchangé |
| 17 | Envoi en cours label | OK | submitLabel | modal | — |
| 18 | onSent ne reset pas form | OK | formInitializedRef | modal | — |
| 19 | Sync 30s non coupable | OK audit | notifications only | `SyncProvider` | — |
| 20 | Pas `location.reload` | OK audit | — | — | — |
| 21 | Hors SalesPilot/Home/Launcher | OK | fichiers touchés | — | — |
| 22 | Pas A1.2 | OK | STOP | — | — |
| 23 | vitest productPhase | OK | run | — | — |
| 24 | vitest emailComposerDraft | OK | run | — | — |
| 25 | tsc | OK | `tsc -b` | — | — |
| 26 | build FE | OK | `npm run build` | — | — |
| 27 | Logs DEV ciblés | OK | `[EmailComposer]` | modal | pas de body/token |
| 28 | CSS dirty bar | OK | `index.css` | — | — |
| 29 | DevisPage réutilise modal | OK | même composant | — | bénéficie du fix |
| 30 | Doc écrite | OK | ce fichier | — | — |
| 31 | Mailto sans `+` (encodeURIComponent) | OK | vitest | `mailtoComposer.test.ts` | A1.1.2 |
| 32 | Confirmation avant Outlook | OK code | `ConfirmDialog` | modal | PDF + attach manuel |
| 33 | Corps client sans jargon mailto | OK | vitest + modal | `mailtoComposer.ts` | — |
| 34 | Nom PDF download override | OK code | `preferredFilename` | `api.ts` | — |

---

## TABLEAU B — Tests manuels Chris (M01–M20)

| ID | Étape | Résultat attendu | Résultat observé | Note/5 | Statut | Capture | Commentaire |
|----|-------|------------------|------------------|--------|--------|---------|-------------|
| M01 | Ouvrir facture → Envoyer | Formulaire visible | — | — | À tester manuellement | — | — |
| M02 | Remplir destinataire/objet/corps | Champs restent | — | — | À tester manuellement | — | — |
| M03 | Attendre 30 s sans focus | Formulaire intact | — | — | À tester manuellement | — | — |
| M04 | Changer d’onglet navigateur puis revenir | Formulaire intact, modal ouverte | — | — | À tester manuellement | — | Cause focus |
| M05 | Autre section nav puis retour facturation | Si dirty confirm ou draft | — | — | À tester manuellement | — | — |
| M06 | Notification / sync pendant saisie | Pas de reset | — | — | À tester manuellement | — | — |
| M07 | Escape avec dirty | Confirm Continuer/Abandonner | — | — | À tester manuellement | — | — |
| M08 | Continuer | Modal + champs conservés | — | — | À tester manuellement | — | — |
| M09 | Abandonner | Fermeture + draft clear | — | — | À tester manuellement | — | — |
| M10 | Backdrop clic si dirty | Pas de fermeture silencieuse | — | — | À tester manuellement | — | — |
| M11 | Fermer puis rouvrir même facture | Draft restauré | — | — | À tester manuellement | — | sessionStorage |
| M12 | Envoi succès | Hint OK, draft clear | — | — | À tester manuellement | — | — |
| M13 | Envoi échec SMTP/Brevo | Champs + erreur + Retry | — | — | À tester manuellement | — | — |
| M14 | Double-clic Envoyer | Un seul envoi | — | — | À tester manuellement | — | — |
| M15 | Modifier (dirty) | Confirm avant quit | — | — | À tester manuellement | — | — |
| M16 | Marquer payée (dirty) | Confirm avant quit | — | — | À tester manuellement | — | — |
| M17 | Mobile onglet Actions | Pas de reset auto vers Aperçu | — | — | À tester manuellement | — | — |
| M18 | Org/doc isolation draft | Autre facture = autre draft | — | — | À tester manuellement | — | — |
| M19 | DevTools : pas de reload page | Network abo silencieux | — | — | À tester manuellement | — | — |
| M20 | Console DEV logs composer | Events sans PII | — | — | À tester manuellement | — | — |

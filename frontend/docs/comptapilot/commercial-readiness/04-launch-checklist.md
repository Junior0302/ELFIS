# 04 — Checklist go / no-go (essai commercial 7 jours)

Objectif : décider si un client réel peut utiliser ComptaPilot **une semaine** sans filet technique permanent.  
**Mis à jour après C1.1 + A1.1 (parcours client).**

Réponses : **OK** / **KO** / **RUNTIME** (à tester sur l’env cible).

---

## A. Prérequis plateforme (ops)

| # | Critère | Statut attendu | Comment vérifier |
|---|---|---|---|
| A1 | Backend + FE joignables | RUNTIME | Login `/login` |
| A2 | Firebase auth / inscription | RUNTIME | `/register` |
| A3 | Essai activable (Stripe ou grant admin) | RUNTIME | `/abonnement`, `/welcome` |
| A4 | SMTP / Brevo plateforme | RUNTIME (sinon mailto OK code) | Envoi devis : serveur **ou** fallback mailto |
| A5 | Stockage Vault | RUNTIME | Archiver PDF `/documents` |
| A6 | Au moins 1 provider banque configuré **ou** exclusion banque du scope | RUNTIME | `/banque` providers `ok` |

Sans **A3**, essai commercial **NO-GO**. Sans A4 : mailto acceptable si client informé.

---

## B. Parcours métier minimal (must)

| # | Critère | Go si | Preuve route |
|---|---|---|---|
| B1 | Créer organisation | OK code | `/register` |
| B2 | Compléter fiche entreprise | OK code | `/organisation`, onboarding |
| B3 | Créer / modifier / supprimer client | OK code | `/clients` |
| B4 | Créer fournisseur autonome | **OK code** | `/fournisseurs` |
| B5 | Créer devis avec lignes | **OK code** | `/devis`, `/facturation` |
| B6 | Modifier / supprimer devis | OK code | `/devis` |
| B7 | Dupliquer devis | **OK code** | Bouton Dupliquer (A1.1) |
| B8 | Convertir devis → facture | OK code | `convert` |
| B9 | Envoyer facture par e-mail | OK code (SMTP ou mailto) | Modal preview |
| B10 | PDF lisible + mentions | RUNTIME | PDF + org remplie |
| B11 | Archiver document | OK code | Vault |
| B12 | Rechercher | OK code | `/search` |
| B13 | Importer + corriger OCR | RUNTIME | `/deposit` → `/result/:id` |
| B14 | Valider proposition écriture | RUNTIME | `/accounting/proposals/:id` |
| B15 | Enregistrer paiement facture | **OK code** (montant / date / réf.) | `InvoicePaymentModal` → `pay` |
| B16 | Consulter banque | RUNTIME | `/banque` |
| B17 | Préparer TVA / clôturer période | **OK MVP** | `/tva`, `/cloture` |

---

## C. Décision

### GO parcours Client→Paiement (A1.1)

**Oui** si A3 + (A4 ou mailto accepté) et org avec SIRET/adresse (ou ack temporaire). Score parcours **97 / 100**.

### GO conditionnel produit élargi (après C1.1)

Autoriser si :

- [ ] Essai activé pour l’org pilote (A3 OK)
- [ ] SMTP testé **ou** client acceptant mailto + PDF joint manuel
- [ ] Scope écrit : ventes multi-lignes, fournisseurs, TVA/clôture **MVP** (pas CA3 / pas verrou fiscal)
- [ ] Banque réelle seulement si provider OK, sinon hors pitch
- [ ] Support dédié OCR / PDF / envois
- [ ] Durée ≤ 7 j

### GO plein parcours production

**Non** tant que P1 critiques restants (essai, banque, OCR) + fiscal dur (CA3, verrou) non traités.

### NO-GO

Si A3 échoue, ou si le brief exige CA3 / clôture légale verrouillée.

---

## D. Smoke test 30 minutes

1. Register → activer essai → `/organisation`.
2. `/clients` + `/fournisseurs` créer 1 fiche chacun.
3. `/catalogue` article → `/facturation` facture multi-lignes (catalogue) → PDF → Envoyer.
4. Marquer Payé.
5. `/deposit` → `/result/:id` → proposition compta.
6. `/tva` export + marquage ; `/cloture` checklist.
7. `/search` + `/finance`.

---

## E. Signaux d’arrêt immédiat

- Envoi e-mail en échec répété (`email_failed` / SMTP)
- PDF illisible / mentions légales manquantes
- Essai expiré / entitlement coupe le produit
- Perte de documents Vault
- Isolation org compromise — escalade sécu

---

## Verdict checklist

| Mode | Verdict |
|---|---|
| Parcours Client → Devis → Facture → Envoi → Paiement | **GO** (A1.1) |
| Semaine commerciale annoncée (parcours demo élargi) | **GO conditionnel** |
| Pilot ventes + achats + TVA MVP | **GO conditionnel** |
| Production sans réserve / fiscal CA3 | **NO-GO** |

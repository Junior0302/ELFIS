# 05 — Recommandations ordonnées (sans code)

Ordre destiné à débloquer un **essai commercial 7 jours** crédible, puis un GO plus large.  
Aucun chantier démarré ici — PHASE C1 s’arrête après ce document.

---

## Vague 0 — Ops / runtime (avant tout code)

1. Vérifier activation essai (Stripe / grant) sur org pilote.
2. Configurer et tester SMTP/Brevo + envoi réel d’une facture.
3. Vérifier Vault + PDF branding avec org complète.
4. Lister providers banque `ok` ; sinon exclure banque du pitch.

**Critère de sortie :** smoke test section D de `04-launch-checklist.md` vert.

---

## Vague 1 — Débloquer la facture commerciale (P0-2 + P0-6 + P0-3)

Priorité absolue produit :

1. **Lignes de document** dans `/devis` et `/facturation` (brancher `lines` déjà supporté BE/PDF).
2. **Sélection catalogue** → préremplir lignes.
3. **Envoi e-mail fiable** : SMTP ops **ou** fallback mailto / connexion Gmail-Outlook self-serve + aligner copies (`DevisPage`, `SettingsPage`).

**Critère :** un artisan peut éditer une facture multi-lignes et l’envoyer.

---

## Vague 2 — Achats & contacts (P0-1)

1. Page **Fournisseurs** (CRUD) miroir `/clients`, indexée search.
2. Brancher l’étape launch `first_supplier` (`action_path`).
3. Conserver le flux OCR → suggestion contact comme accélérateur.

**Critère :** onboarding achats sans passer par un dépôt document.

---

## Vague 3 — Fiabiliser le cœur semaine (P1)

1. ~~Dupliquer devis.~~ **Fait A1.1**
2. Remplacer timers faux de `/deposit` par statut réel (ou retirer le faux pipeline).
3. ~~UI paiement partiel (montant, date, référence).~~ **Fait A1.1**
4. Clarifier plan OCR Trial vs Professional (feature flag vs réalité upload).
5. Rapprochement bancaire manuel minimal (liste non réconciliés).
6. ~~Copy mailto + garde mentions légales.~~ **Fait A1.1**

---

## Vague 4 — Fiscalité annoncée (P0-4 + P0-5)

1. **TVA** : écran période (collectée / déductible / solde) + export — avant CA3 complète.
2. **Clôture** : verrouillage période + checklist (même V0 manuelle).
3. Retirer ou reformuler les promesses marketing « clôture » tant que non livré.

**Critère :** le mot « TVA / clôture » dans le pitch correspond à un écran réel.

---

## Vague 5 — Durcissement commercial

1. Export comptable sur plan d’essai si promis.
2. Mentions légales obligatoires avant envoi PDF.
3. Multi-user si plusieurs personnes testent.
4. Bridge document produit uniquement si besoin d’intégration externe.

---

## Ce qu’il ne faut pas faire maintenant

- Étendre SalesPilot / plateforme shell pendant ces vagues.
- Promettre déclaration fiscale complète sans Vague 4.
- Lancer un client sans Vague 0 (SMTP + essai).
- Traiter P3 cosmétiques avant P0.

---

## Séquençage suggéré (calendrier indicatif)

| Semaine | Focus |
|---|---|
| S0 | Vague 0 runtime |
| S1–S2 | Vague 1 facture + e-mail |
| S2–S3 | Vague 2 fournisseurs |
| S3–S4 | Vague 3 P1 cœur |
| S5+ | Vague 4 fiscalité |

Réévaluer go/no-go après Vague 1+2 : un **pilot 7 j ventes+achats** devient envisageable ; GO fiscal reste plus tard.

---

## Synthèse recommandation

| Question | Réponse |
|---|---|
| Commercialisable aujourd’hui ? | **GO** parcours client (A1.1) ; **GO conditionnel** produit élargi |
| Prochaine action ? | Vague 0 runtime (SMTP + essai) puis autres parcours (OCR/banque) sur demande |
| Implémentation P0 ? | **Faite** — `06-p0-remediation-report.md` |
| Parcours client P1 ? | **Faite** — `07-customer-journey-remediation.md` |

---

## Index des livrables C1 / C1.1

| Fichier | Rôle |
|---|---|
| `README.md` | Verdict & méthode |
| `01-user-journey.md` | Parcours ✅⚠❌ |
| `02-critical-blockers.md` | P0 / P1 critiques |
| `03-priority-matrix.md` | Matrice complète |
| `04-launch-checklist.md` | Go / no-go |
| `05-recommendations.md` | Ce fichier |
| `06-p0-remediation-report.md` | Rapport remediation P0 (C1.1) |
| `07-customer-journey-remediation.md` | Rapport parcours client (A1.1) |
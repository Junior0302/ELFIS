# 09 — Tests LD01–LD40

## Automatisés

| Suite | Fichier |
|-------|---------|
| Live helpers / totaux / insights / status | `live-document/live-document.test.tsx` |
| Composer preview + contrôles FE | `composer-framework.test.tsx` |
| Workflow totaux / controls (non-régression) | `workflow.test.ts` |
| Pickers / Insight (non-régression) | platform-search / insight-framework tests |

## Manuels « À tester manuellement »

| ID | Scénario |
|----|----------|
| LD01 | Ouvrir `/facturation/nouveau` — layout Composer + focus |
| LD02 | Choisir type document → aperçu live se met à jour |
| LD03 | Sélectionner client via CustomerPicker sans quitter Composer |
| LD04 | Résumé client (email / tél / adresse) visible |
| LD05 | Créer client local in-composer |
| LD06 | Rechercher produit ProductPicker (Smart Library) |
| LD07 | Sélection produit → ligne + aperçu dernier pick |
| LD08 | Création produit locale sans navigation catalogue obligatoire |
| LD09 | Modifier qté → totaux + preview live immédiats |
| LD10 | Modifier prix → idem |
| LD11 | Modifier remise → remises + TTC |
| LD12 | Modifier TVA document → TVA / TTC |
| LD13 | Modifier notes → preview live |
| LD14 | Modifier échéance → label date calendaire |
| LD15 | Flash totaux discret ; reduced-motion OK |
| LD16 | Insight « client sélectionné » apparaît |
| LD17 | Insight « produit ajouté » apparaît |
| LD18 | TVA 12 % → insight « inhabituelle » |
| LD19 | HT > 50k → insight montant élevé |
| LD20 | Pas d’insight « document similaire » inventé |
| LD21 | Enregistrer brouillon → statut Brouillon / Prêt |
| LD22 | Autosave : Enregistrement… puis Sauvegardé |
| LD23 | Simuler erreur save → Erreur + Nouvelle tentative |
| LD24 | Après update, PDF se rafraîchit (debounce) sans reload page |
| LD25 | Toggle Live / PDF |
| LD26 | Zoom + / − / 100 % |
| LD27 | Fit width |
| LD28 | Page `#page=N` (best-effort) |
| LD29 | Plein écran panneau preview |
| LD30 | Télécharger PDF |
| LD31 | Statut Validation requise si warning |
| LD32 | Envoyer → statut Envoyé |
| LD33 | Aria-live totaux / save / insights (lecteur d’écran) |
| LD34 | Responsive laptop : collapse preview |
| LD35 | Mobile : édition + totaux lisibles |
| LD36 | Focus mode inchangé |
| LD37 | Aucune régression étape wizard navigation |
| LD38 | Build `npm run build` vert |
| LD39 | Tests ciblés live-document + composer verts |
| LD40 | Pas de début F1.4 / pas de nouveau Framework |

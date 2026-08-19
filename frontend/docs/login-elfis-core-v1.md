# P1.4 — ELFIS Core Login Experience V1

## 1 — Audit

| Élément | Constat | Décision |
|---------|---------|----------|
| `LoginPage` (ancienne) | Carte seule dans `AuthLayout`, copy OK ELFIS | Remplacée par module `src/login/` |
| `AuthLayout` | Aside sombre + **GSAP** ; overrides `--elfis` partiels ; CSS legacy vert | Login sorti du layout ; register/forgot gardent AuthLayout sans GSAP, textes ELFIS |
| `AuthProvider` / Firebase / `/api/auth/firebase` | Flux réel correct | **Conservé** (non modifié) |
| `mapLoginFailure` | Timeout, invalid-credential, backend | **Conservé** |
| Redirection | invite → `/compte` ; sinon `/dashboard` ; `state.from` ignoré | **Conservé** + `state.from` si sûr |
| Forgot / Register | Routes AuthLayout | Liens préservés |
| Theme `/login` | `elfis-core` via RuntimeThemeSync | Inchangé |
| Asset marque | `/favicon.svg` (ComptaPilot shell) | **Conservé** comme Landing V1 |
| Dominante verte | `.auth-shell` / cards legacy forest | Login : navy/clair ; AuthLayout elfis étendu |

**Conservé :** flux auth, messages erreur, anti double-clic, loading reset, invite.  
**Retiré du login :** AuthLayout + GSAP, typo Fraunces/vert, copy « Pilotez vos chiffres ».  
**Nouveau :** panel marque + illustration Pilot + FormField/Input/Button DS.

## 2 — Structure

```
src/login/
  LoginPage.tsx
  LoginBrandPanel.tsx
  LoginForm.tsx
  LoginBenefit.tsx
  LoginIllustration.tsx
  login.css
  index.ts
pages/LoginPage.tsx  → re-export
App.tsx              → /login hors AuthLayout
```

## 3 — Desktop / Mobile

- Desktop : grille 2 colonnes (héro + carte).  
- Mobile : formulaire d’abord (`order: -1`), bénéfices masqués, illu réduite, CTA pleine largeur.

## 4 — Identité

Surfaces claires, navy `#0B1F3A`, accent `#3D7EFF`, pastilles Pilot (bleu/vert/orange/violet) **ponctuelles**, logo `/favicon.svg`.

## 5 — Flux auth

Firebase email/mdp → idToken → `POST /api/auth/firebase` → session → navigate.

## 6 — Dette restante

- Register / Forgot : encore layout split sombre (navy), pas le split clair du login.  
- SSO Google/Microsoft : hors scope.  
- Compte désactivé : message générique Firebase si non mappé.  
- Lighthouse login : non rejoué en CI (tests unitaires + build).

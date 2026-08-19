# ELFIS Core — Test identité & stabilité thème V1

## 1. Démarrage

```bat
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

## 2. Nettoyage localStorage thème

DevTools → Application → Local Storage → supprimer `elfis.design-system.current-product`.

## 3. Login (30 s)

1. Ouvrir `/login`
2. Vérifier marque **ELFIS Core** (pas ComptaPilot)
3. Console : `data-product=elfis-core`, `--pilot-primary` navy
4. Attendre 30 s — **aucune** oscillation de couleur

## 4. ComptaPilot (30 s)

1. Se connecter
2. `/dashboard` → vert stable, `data-product=comptapilot`
3. Attendre 30 s

## 5. Launcher → SalesPilot (30 s)

1. Ouvrir App Launcher → SalesPilot
2. URL `/sales`, `data-product=salespilot`, sidebar bleue
3. Un seul log `[ELFIS Theme]` route_change
4. Attendre 30 s — pas de flash vert

## 6. Retour ComptaPilot

1. Lien ← ComptaPilot ou Launcher
2. Un seul passage bleu → vert
3. Attendre 30 s

## 7. Refresh / nouvel onglet

1. Sur `/sales`, F5 → reste bleu
2. Nouvel onglet `/sales` → bleu dès le premier paint (bootstrap)

## 8. Logout

1. Déconnexion → `/login` identité ELFIS Core

## Diagnostic si oscillation

1. Chercher `[ELFIS Theme] Oscillation détectée`
2. Vérifier qu’un seul `ProductThemeProvider` racine existe
3. Vérifier qu’aucun layout n’appelle `setCurrentProduct`
4. Vérifier l’absence de `clearProductTheme` au unmount

# 04 — Plan de tests collapse sidebar (UI.P1)

## Automatisés (SC01–SC40)

Fichier : `frontend/src/platform-shell/sidebar-collapse.test.tsx`

| ID | Cas |
|----|-----|
| SC01 | Token expanded 240px |
| SC02 | Token collapsed 52–64px (56) |
| SC03 | `--product-sidebar-current-width` |
| SC04 | `--ps-sidebar-w` alias current |
| SC05 | Grid `current minmax(0,1fr)` |
| SC06 | `.ps-shell--sidebar-collapsed` override |
| SC07 | Transition 180ms |
| SC08 | `prefers-reduced-motion` |
| SC09 | Labels `display:none` |
| SC10 | Mobile grid 1fr même collapsed |
| SC11–14 | Storage read/write + migration legacy |
| SC15–18 | Classe shell + hydrate sans flash |
| SC19–20 | `aria-expanded` / `aria-controls` |
| SC21–22 | Toggle collapse / expand |
| SC23–26 | Events resize viewport |
| SC27 | Topbar hors body grid |
| SC28–29 | overflow-x / pas margin hardcodée |
| SC30 | Clé `elfis.productSidebarCollapsed` |
| SC31 | Pas de redirect route |
| SC32–34 | Prop `sidebarCollapsed` PlatformShell |
| SC35 | CSS icônes centrées |
| SC36 | ResizeObserver viewport |
| SC37–38 | Valeurs storage |
| SC39 | Overlay mobile fixed |
| SC40 | Label / title dynamiques |

```bash
npx vitest run src/platform-shell/sidebar-collapse.test.tsx
```

## Manuels — À tester manuellement (SM01–SM20)

| ID | Scénario |
|----|----------|
| SM01 | Desktop : collapse → bande vide disparaît immédiatement |
| SM02 | Desktop : expand → rail 240px + labels |
| SM03 | Transition fluide 180ms (œil) |
| SM04 | `prefers-reduced-motion` : pas d’anim largeur |
| SM05 | Dashboard FCC : graphs se ré-étalent sans F5 |
| SM06 | Scroll horizontal page absent après collapse |
| SM07 | Topbar reste pleine largeur |
| SM08 | Item actif visible en rail icônes |
| SM09 | Tooltip / title au survol icône collapsed |
| SM10 | Focus clavier bouton collapse + items |
| SM11 | Flyout sous-menu collapsed (souris) |
| SM12 | Persistance après reload |
| SM13 | Pas de flash expanded→collapsed au reload |
| SM14 | Mobile : drawer overlay, contenu 100 % fermé |
| SM15 | Mobile : ouvrir/fermer via bouton « Navigation » contenu (UI.P2) |
| SM16 | Tablette ≤900px : pas de colonne réservée fermée |
| SM17 | Navigation entre pages Compta : état collapse conservé |
| SM18 | SalesPilot : layout inchangé (pas de collapse Compta) |
| SM19 | Trial onboarding : collapse toujours sync si sidebar présente |
| SM20 | Zoom 125 % / fenêtre étroite desktop : pas de bande morte |

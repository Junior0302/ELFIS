import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './design-system/components/components.css'
import './design-system/overlays/styles/overlays.css'
import './design-system/colors/elfis-brand.css'
import './workspaces/workspace-accents.css'
import './workspaces/workspace-space-icon.css'
import './workspaces/workspace-surface.css'
import App from './App.tsx'
import { logBuildBanner } from './buildInfo'
import { bootstrapRuntimeProductTheme } from './design-system/themes/bootstrapRuntimeProductTheme'

// Remet le thème clair d’origine (annule un éventuel mode sombre stocké).
try {
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.style.colorScheme = 'light'
  localStorage.removeItem('cp_theme')
} catch {
  /* ignore */
}

// Apply route product tokens BEFORE React mount (same resolution as RuntimeThemeSync).
bootstrapRuntimeProductTheme()

logBuildBanner()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

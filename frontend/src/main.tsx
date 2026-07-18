import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Remet le thème clair d’origine (annule un éventuel mode sombre stocké).
try {
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.style.colorScheme = 'light'
  localStorage.removeItem('cp_theme')
} catch {
  /* ignore */
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

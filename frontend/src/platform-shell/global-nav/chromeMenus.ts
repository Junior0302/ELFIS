/** Ferme overlays Overlay Manager + menus chrome locaux (UserMenu, notifications). */
export const ELFIS_CLOSE_CHROME_MENUS = 'elfis:close-chrome-menus'

export function closeChromeMenus(): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(ELFIS_CLOSE_CHROME_MENUS))
}

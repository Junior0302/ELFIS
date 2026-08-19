/**
 * Keyboard helpers — ↑↓ Enter Escape Tab.
 * Cmd/Ctrl+K reste propriété exclusive du Command Center (pas de 2e raccourci global).
 */

export type ListKeyboardHandlers = {
  itemCount: number
  activeIndex: number
  setActiveIndex: (index: number) => void
  onSelect: (index: number) => void
  onEscape?: () => void
  onTab?: () => void
}

export function handleListKeyboard(
  e: { key: string; preventDefault: () => void; stopPropagation?: () => void },
  handlers: ListKeyboardHandlers,
): boolean {
  const { itemCount, activeIndex, setActiveIndex, onSelect, onEscape, onTab } = handlers
  if (itemCount <= 0 && e.key !== 'Escape' && e.key !== 'Tab') return false

  switch (e.key) {
    case 'ArrowDown': {
      e.preventDefault()
      if (itemCount === 0) return true
      setActiveIndex(activeIndex < itemCount - 1 ? activeIndex + 1 : 0)
      return true
    }
    case 'ArrowUp': {
      e.preventDefault()
      if (itemCount === 0) return true
      setActiveIndex(activeIndex > 0 ? activeIndex - 1 : itemCount - 1)
      return true
    }
    case 'Enter': {
      if (activeIndex >= 0 && activeIndex < itemCount) {
        e.preventDefault()
        onSelect(activeIndex)
        return true
      }
      return false
    }
    case 'Escape': {
      e.preventDefault()
      onEscape?.()
      return true
    }
    case 'Tab': {
      onTab?.()
      return false
    }
    default:
      return false
  }
}

/** Documente : ne pas enregistrer Cmd/Ctrl+K ici. */
export const GLOBAL_SHORTCUT_OWNER = 'platform-command/CommandCenter' as const

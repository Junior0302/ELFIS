/** Focus helpers for modal overlays. */

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true',
  )
}

export function focusFirstElement(container: HTMLElement): void {
  const items = getFocusableElements(container)
  ;(items[0] ?? container).focus()
}

export function focusLastElement(container: HTMLElement): void {
  const items = getFocusableElements(container)
  ;(items[items.length - 1] ?? container).focus()
}

export function restoreFocus(target: HTMLElement | null | undefined): void {
  if (!target) return
  try {
    if (document.contains(target)) target.focus()
  } catch {
    /* ignore */
  }
}

export function trapTabKey(event: KeyboardEvent, container: HTMLElement): void {
  if (event.key !== 'Tab') return
  const items = getFocusableElements(container)
  if (items.length === 0) {
    event.preventDefault()
    container.focus()
    return
  }
  const first = items[0]!
  const last = items[items.length - 1]!
  const active = document.activeElement as HTMLElement | null
  if (event.shiftKey) {
    if (active === first || !container.contains(active)) {
      event.preventDefault()
      last.focus()
    }
  } else if (active === last) {
    event.preventDefault()
    first.focus()
  }
}

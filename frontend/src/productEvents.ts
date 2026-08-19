/**
 * Événements produit légers — pas de nouvel outil analytics.
 * Journalise en console (dev) et pousse vers un buffer mémoire + window si présent.
 */

export type ProductEventName =
  | 'trial_onboarding_viewed'
  | 'trial_cta_clicked'
  | 'locked_nav_item_clicked'
  | 'feature_discovery_opened'
  | 'trial_activation_completed'
  | 'app_launcher.opened'
  | 'app_launcher.closed'
  | 'app_launcher.product_selected'
  | 'app_launcher.coming_soon_viewed'
  | 'app_launcher.searched'
  | 'app_launcher.unavailable_clicked'
  | 'command_center.open'
  | 'command_center.search'
  | 'command_center.navigate'
  | 'command_center.close'

export type ProductEventPayload = Record<string, string | number | boolean | null | undefined>

export type ProductEventEntry = {
  name: ProductEventName
  at: string
  payload?: ProductEventPayload
}

const memoryBuffer: ProductEventEntry[] = []

declare global {
  interface Window {
    __cpProductEvents?: ProductEventEntry[]
  }
}

export function getProductEvents(): ProductEventEntry[] {
  if (typeof window !== 'undefined' && window.__cpProductEvents) {
    return window.__cpProductEvents
  }
  return memoryBuffer
}

export function clearProductEvents(): void {
  memoryBuffer.length = 0
  if (typeof window !== 'undefined') window.__cpProductEvents = []
}

export function trackProductEvent(name: ProductEventName, payload?: ProductEventPayload): void {
  const entry: ProductEventEntry = { name, at: new Date().toISOString(), payload }
  memoryBuffer.push(entry)
  if (memoryBuffer.length > 200) memoryBuffer.splice(0, memoryBuffer.length - 200)
  try {
    if (typeof window !== 'undefined') {
      window.__cpProductEvents = window.__cpProductEvents || []
      window.__cpProductEvents.push(entry)
      if (window.__cpProductEvents.length > 200) {
        window.__cpProductEvents.splice(0, window.__cpProductEvents.length - 200)
      }
    }
  } catch {
    /* ignore */
  }
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.info('[ComptaPilot product]', name, payload || {})
  }
}

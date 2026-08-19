import { useEffect, useState } from 'react'

/** Debounce générique — défaut 280 ms (aligné Command Center). */
export function useDebouncedValue<T>(value: T, delayMs = 280): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs)
    return () => window.clearTimeout(t)
  }, [value, delayMs])
  return debounced
}

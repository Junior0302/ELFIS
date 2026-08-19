/**
 * Reference-counted body scroll lock.
 * Avoids scrollbar jump by compensating with padding-right.
 */

let lockCount = 0
let previousOverflow = ''
let previousPaddingRight = ''

export function lockBodyScroll(): () => void {
  if (typeof document === 'undefined') return () => undefined

  if (lockCount === 0) {
    const body = document.body
    previousOverflow = body.style.overflow
    previousPaddingRight = body.style.paddingRight
    const scrollbarGap =
      document.documentElement.clientWidth > 0
        ? Math.max(0, window.innerWidth - document.documentElement.clientWidth)
        : 0
    body.style.overflow = 'hidden'
    if (scrollbarGap > 0 && scrollbarGap < 80) {
      body.style.paddingRight = `${scrollbarGap}px`
    }
  }
  lockCount += 1

  let released = false
  return () => {
    if (released) return
    released = true
    lockCount = Math.max(0, lockCount - 1)
    if (lockCount === 0 && typeof document !== 'undefined') {
      document.body.style.overflow = previousOverflow
      document.body.style.paddingRight = previousPaddingRight
    }
  }
}

/** Test helper */
export function __resetScrollLockForTests(): void {
  lockCount = 0
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
    document.body.style.paddingRight = ''
  }
}

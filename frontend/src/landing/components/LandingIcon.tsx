const ICONS = {
  shield: (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3.5 5.5 6v5.2c0 4.1 2.7 7.8 6.5 9.3 3.8-1.5 6.5-5.2 6.5-9.3V6L12 3.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="m9.2 12 1.8 1.8 3.8-3.8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  link: (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M9 12h6M10 8H8a4 4 0 0 0 0 8h2M14 8h2a4 4 0 0 1 0 8h-2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  ),
  building: (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 20h16M6 20V6.5A1.5 1.5 0 0 1 7.5 5h9A1.5 1.5 0 0 1 18 6.5V20"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M9 9h2M13 9h2M9 13h2M13 13h2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  database: (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <ellipse cx="12" cy="6" rx="6.5" ry="2.4" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5.5 6v6c0 1.3 2.9 2.4 6.5 2.4s6.5-1.1 6.5-2.4V6" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M5.5 12v6c0 1.3 2.9 2.4 6.5 2.4s6.5-1.1 6.5-2.4v-6"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  ),
  spark: (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  ),
  grid: (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="4" y="4" width="6" height="6" rx="1.2" stroke="currentColor" strokeWidth="1.6" />
      <rect x="14" y="4" width="6" height="6" rx="1.2" stroke="currentColor" strokeWidth="1.6" />
      <rect x="4" y="14" width="6" height="6" rx="1.2" stroke="currentColor" strokeWidth="1.6" />
      <rect x="14" y="14" width="6" height="6" rx="1.2" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  ),
} as const

export type LandingIconName = keyof typeof ICONS

export function LandingIcon({ name }: { name: LandingIconName }) {
  return ICONS[name]
}

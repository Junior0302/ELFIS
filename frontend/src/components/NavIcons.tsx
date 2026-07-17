import type { ReactNode } from 'react'

type IconProps = { className?: string }

function Svg({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  )
}

export const NavIconDashboard = ({ className }: IconProps) => (
  <Svg className={className}>
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </Svg>
)

export const NavIconIntelligence = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 3v2" />
    <path d="M12 19v2" />
    <path d="M5 12H3" />
    <path d="M21 12h-2" />
    <circle cx="12" cy="12" r="5.5" />
    <path d="M9.5 12.5 11 14l3.5-3.5" />
  </Svg>
)

export const NavIconCopilote = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M21 15a4 4 0 0 1-4 4H8l-4 3V7a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4z" />
    <path d="M8 9h8M8 13h5" />
  </Svg>
)

export const NavIconDeposit = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 16V4" />
    <path d="m7 9 5-5 5 5" />
    <path d="M4 20h16" />
  </Svg>
)

export const NavIconHistory = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    <path d="M8 7h8M8 11h6" />
  </Svg>
)

export const NavIconBilling = ({ className }: IconProps) => (
  <Svg className={className}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="M3 10h18" />
    <path d="M7 15h4" />
  </Svg>
)

export const NavIconQuotes = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
    <path d="M8 13h8M8 17h5" />
  </Svg>
)

export const NavIconClients = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="9" cy="8" r="3.5" />
    <path d="M2.5 19a6.5 6.5 0 0 1 13 0" />
    <circle cx="17" cy="9" r="2.5" />
    <path d="M16 19a5 5 0 0 1 5.5-4.8" />
  </Svg>
)

export const NavIconCatalog = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M4 7h16" />
    <path d="M4 12h16" />
    <path d="M4 17h10" />
    <circle cx="18" cy="17" r="2" />
  </Svg>
)

export const NavIconActivities = ({ className }: IconProps) => (
  <Svg className={className}>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M8 3v4M16 3v4M3 11h18" />
    <path d="M8 15h2M12 15h2" />
  </Svg>
)

export const NavIconSubscription = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Svg>
)

export const NavIconOrg = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M3 21h18" />
    <path d="M5 21V8l7-4 7 4v13" />
    <path d="M9 21v-6h6v6" />
  </Svg>
)

export const NavIconTeam = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="3.5" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a3.5 3.5 0 0 1 0 6.74" />
  </Svg>
)

export const NavIconSettings = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V20a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H4a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V4a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H20a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
  </Svg>
)

export const NavIconAccount = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20a8 8 0 0 1 16 0" />
  </Svg>
)

export const navIcons: Record<string, (props: IconProps) => ReactNode> = {
  '/dashboard': NavIconDashboard,
  '/intelligence': NavIconIntelligence,
  '/copilote': NavIconCopilote,
  '/deposit': NavIconDeposit,
  '/history': NavIconHistory,
  '/facturation': NavIconBilling,
  '/devis': NavIconQuotes,
  '/clients': NavIconClients,
  '/catalogue': NavIconCatalog,
  '/activites': NavIconActivities,
  '/abonnement': NavIconSubscription,
  '/organisation': NavIconOrg,
  '/admin/equipe': NavIconTeam,
  '/settings': NavIconSettings,
  '/compte': NavIconAccount,
}

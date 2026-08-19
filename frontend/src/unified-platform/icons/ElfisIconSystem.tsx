/**
 * Mapping icônes central — réutilise NavIcons Compta + glyphs plateforme.
 * Un seul registre ; les Pilots ne branchent pas de lib ad hoc.
 */

import type { ReactNode } from 'react'
import { navIcons } from '../../components/NavIcons'

export type ElfisIconId =
  | keyof typeof PLATFORM_ICON_GLYPHS
  | string

/** Glyphs texte (Home / nav Core / Sales collapsed) — pas une 2e lib SVG. */
export const PLATFORM_ICON_GLYPHS = {
  home: '⌂',
  star: '★',
  apps: '★',
  activity: '◷',
  building: '◈',
  'building-2': '▣',
  users: '♟',
  shield: '⛨',
  user: '☺',
  network: '◎',
  file: '▤',
  bell: '◉',
  mail: '✉',
  settings: '⚙',
  sparkles: '✦',
  'heart-pulse': '♥',
  history: '↺',
  list: '☰',
  search: '⌕',
  'help-circle': '?',
  'log-out': '⎋',
  status: '●',
  sales: 'S',
  compta: 'C',
  dashboard: '▦',
  pipeline: '◇',
  leads: '◎',
  tasks: '☐',
  activities: '☎',
} as const

type IconProps = { className?: string; title?: string }

/** Résout une icône par id / path nav. */
export function resolveElfisIcon(
  id: string | undefined,
  props: IconProps = {},
): ReactNode {
  if (!id) return null
  const Svg = navIcons[id]
  if (Svg) return <Svg className={props.className} />
  const glyph =
    (PLATFORM_ICON_GLYPHS as Record<string, string>)[id] ??
    id.slice(0, 1).toUpperCase()
  return (
    <span className={props.className} aria-hidden title={props.title}>
      {glyph}
    </span>
  )
}

export function ElfisIcon({
  id,
  className,
  title,
}: {
  id: string
  className?: string
  title?: string
}) {
  return <>{resolveElfisIcon(id, { className, title })}</>
}

/** Mapping path → icon id (central). */
export const ELFIS_NAV_ICON_BY_PATH: Record<string, string> = {
  ...Object.fromEntries(Object.keys(navIcons).map((path) => [path, path])),
  '/home': 'home',
  '/notifications': 'bell',
  '/search': 'search',
  '/platform/organization': 'building',
  '/platform/members': 'users',
  '/platform/relations': 'network',
  '/platform/documents': 'file',
  '/platform/communications': 'mail',
  '/platform/aura': 'sparkles',
  '/platform/settings': 'settings',
  '/sales': 'dashboard',
  '/sales/pipeline': 'pipeline',
  '/sales/leads': 'leads',
  '/sales/tasks': 'tasks',
  '/sales/activities': 'activities',
}


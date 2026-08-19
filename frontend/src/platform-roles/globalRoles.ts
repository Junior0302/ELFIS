/**
 * Rôles globaux ELFIS — libellés UI transverses (BRAND.ELFIS.2).
 * Les clés backend (cfo, comptable, …) restent inchangées ; mapping affichage uniquement.
 */

export type GlobalRoleId = 'owner' | 'admin' | 'manager' | 'member' | 'viewer'

/** Ordre d’affichage cartes / légende. */
export const GLOBAL_ROLE_ORDER: readonly GlobalRoleId[] = [
  'owner',
  'admin',
  'manager',
  'member',
  'viewer',
] as const

export type GlobalRoleDef = {
  id: GlobalRoleId
  label: string
  description: string
  protected?: boolean
  /** Clés backend qui s’affichent sous ce rôle global. */
  backendKeys: readonly string[]
  /** Clé backend préférée à l’invitation (hors owner). */
  inviteBackendKey?: string
}

export const GLOBAL_ROLE_DEFS: Record<GlobalRoleId, GlobalRoleDef> = {
  owner: {
    id: 'owner',
    label: 'Propriétaire',
    description:
      'Contrôle complet — organisation, sécurité, abonnement et espaces. Rôle protégé.',
    protected: true,
    backendKeys: ['owner'],
  },
  admin: {
    id: 'admin',
    label: 'Administrateur',
    description: 'Membres, rôles, paramètres, sécurité et abonnements selon permission.',
    backendKeys: ['admin'],
    inviteBackendKey: 'admin',
  },
  manager: {
    id: 'manager',
    label: 'Gestionnaire',
    description:
      'Accès opérationnel étendu et gestion des éléments autorisés, sans contrôle complet de l’organisation.',
    backendKeys: ['cfo'],
    inviteBackendKey: 'cfo',
  },
  member: {
    id: 'member',
    label: 'Collaborateur',
    description: 'Utilisation des espaces attribués — création et modification selon permissions.',
    backendKeys: ['comptable', 'employe'],
    inviteBackendKey: 'employe',
  },
  viewer: {
    id: 'viewer',
    label: 'Lecteur',
    description: 'Consultation seule — aucune modification.',
    backendKeys: ['auditeur'],
    inviteBackendKey: 'auditeur',
  },
}

/** Backend role key → global role id. */
export const BACKEND_ROLE_TO_GLOBAL: Record<string, GlobalRoleId> = {
  owner: 'owner',
  admin: 'admin',
  cfo: 'manager',
  comptable: 'member',
  employe: 'member',
  auditeur: 'viewer',
}

/**
 * Libellés FR pour affichage / API mirror.
 * Remplace « Directeur financier », « Comptable », etc.
 */
export const GLOBAL_ROLE_LABELS_FR: Record<string, string> = {
  owner: GLOBAL_ROLE_DEFS.owner.label,
  admin: GLOBAL_ROLE_DEFS.admin.label,
  cfo: GLOBAL_ROLE_DEFS.manager.label,
  comptable: GLOBAL_ROLE_DEFS.member.label,
  employe: GLOBAL_ROLE_DEFS.member.label,
  auditeur: GLOBAL_ROLE_DEFS.viewer.label,
  /* Aliases cible (si enums futurs) */
  manager: GLOBAL_ROLE_DEFS.manager.label,
  member: GLOBAL_ROLE_DEFS.member.label,
  viewer: GLOBAL_ROLE_DEFS.viewer.label,
}

export function resolveGlobalRoleId(backendRole: string): GlobalRoleId | null {
  return BACKEND_ROLE_TO_GLOBAL[backendRole] ?? null
}

export function globalRoleLabel(backendRole: string): string {
  return (
    GLOBAL_ROLE_LABELS_FR[backendRole] ||
    GLOBAL_ROLE_DEFS[backendRole as GlobalRoleId]?.label ||
    backendRole
  )
}

export function globalRoleHelp(backendRole: string): string {
  const id = resolveGlobalRoleId(backendRole)
  return id ? GLOBAL_ROLE_DEFS[id].description : ''
}

/**
 * Options d’invitation dédupliquées (un libellé global = une clé backend préférée).
 * Filtre selon les rôles réellement renvoyés par l’API.
 */
export function inviteRoleOptions(apiRoles: string[]): { value: string; label: string; help: string }[] {
  const available = new Set(apiRoles)
  const out: { value: string; label: string; help: string }[] = []
  for (const id of GLOBAL_ROLE_ORDER) {
    if (id === 'owner') continue
    const def = GLOBAL_ROLE_DEFS[id]
    const key = def.inviteBackendKey
    if (!key || !available.has(key)) {
      /* fallback : première clé backend présente */
      const fallback = def.backendKeys.find((k) => available.has(k))
      if (!fallback) continue
      out.push({ value: fallback, label: def.label, help: def.description })
      continue
    }
    out.push({ value: key, label: def.label, help: def.description })
  }
  return out
}

/**
 * Colonne « Accès aux espaces » — feature flag.
 * false tant qu’aucune capacité / colonne backend n’existe.
 */
export const SPACE_ACCESS_COLUMN_ENABLED =
  typeof import.meta !== 'undefined' &&
  Boolean(import.meta.env?.VITE_ELFIS_SPACE_PERMISSIONS === 'true')

/** Modèle cible documenté (pas de migration tables dans cette phase). */
export type ElfisSpacePermission = 'admin' | 'editor' | 'viewer' | 'none'

export type ElfisMembershipTarget = {
  globalRole: GlobalRoleId
  spaces: {
    finance?: ElfisSpacePermission
    commercial?: ElfisSpacePermission
    documents?: ElfisSpacePermission
    hr?: ElfisSpacePermission
  }
}

import { describe, expect, it } from 'vitest'
import {
  PLATFORM_COCKPIT_PERMISSIONS,
  canSeePlatformNavItem,
  platformCockpitSections,
  resolvePlatformPermissions,
} from './platformCockpitNav'

describe('Platform Cockpit navigation', () => {
  it('expose la sidebar mission', () => {
    const labels = platformCockpitSections.flatMap((s) => s.items.map((i) => i.label))
    for (const label of [
      'Vue globale',
      'Organisations',
      'Utilisateurs',
      'Abonnements',
      'Documents',
      'Migration',
      'Comptabilité',
      'IA',
      'Notifications',
      'Rapports',
      'Santé système',
      'Logs',
      'Support',
      'Configuration',
      'Activity Center',
      'Processing',
      'Storage',
      'Incidents',
      'Audit',
      'Sécurité',
      'Observabilité',
      'Fiabilité',
      'Dev Cockpit',
    ]) {
      expect(labels).toContain(label)
    }
    expect(platformCockpitSections.map((s) => s.title)).toEqual(['Plateforme', 'Ops avancées'])
  })

  it('accorde tout à platform.admin', () => {
    const effective = resolvePlatformPermissions({ isPlatformAdmin: true })
    expect(effective).toContain(PLATFORM_COCKPIT_PERMISSIONS.admin)
    const item = platformCockpitSections[0].items.find((i) => i.to === '/elfadmin/comptabilite')!
    expect(canSeePlatformNavItem(item, effective)).toBe(true)
  })

  it('support ne voit pas la comptabilité', () => {
    const effective = [PLATFORM_COCKPIT_PERMISSIONS.support]
    const accounting = platformCockpitSections[0].items.find((i) => i.to === '/elfadmin/comptabilite')!
    const support = platformCockpitSections[0].items.find((i) => i.to === '/elfadmin/support')!
    expect(canSeePlatformNavItem(accounting, effective)).toBe(false)
    expect(canSeePlatformNavItem(support, effective)).toBe(true)
  })
})

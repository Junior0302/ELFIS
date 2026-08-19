/** Helpers First Business Experience (C1.13). */

export const LAUNCH_SOURCE = 'launch-dashboard'
export const LAUNCH_REFRESH_KEY = 'elfis.launch_dashboard.refresh'

export type FirstExperienceAction = {
  label: string
  to?: string
  onClick?: () => void
  tone?: 'primary' | 'secondary'
}

export function isLaunchDashboardSource(source: string | null | undefined): boolean {
  return (source || '').trim() === LAUNCH_SOURCE
}

/** Appends ?source=launch-dashboard without inventing a new route. */
export function withLaunchSource(path: string): string {
  const raw = (path || '').trim()
  if (!raw || raw.startsWith('http')) return raw
  if (raw.includes(`source=${LAUNCH_SOURCE}`)) return raw
  const hashIdx = raw.indexOf('#')
  const beforeHash = hashIdx >= 0 ? raw.slice(0, hashIdx) : raw
  const hash = hashIdx >= 0 ? raw.slice(hashIdx) : ''
  const sep = beforeHash.includes('?') ? '&' : '?'
  return `${beforeHash}${sep}source=${LAUNCH_SOURCE}${hash}`
}

export function invoicePathForCustomer(customerId: number, fromLaunch = true): string {
  const base = `/facturation?customer_id=${encodeURIComponent(String(customerId))}`
  return fromLaunch ? withLaunchSource(base) : base
}

export function markLaunchDashboardStale(): void {
  try {
    sessionStorage.setItem(LAUNCH_REFRESH_KEY, String(Date.now()))
  } catch {
    /* ignore */
  }
}

export function consumeLaunchDashboardStale(): boolean {
  try {
    const value = sessionStorage.getItem(LAUNCH_REFRESH_KEY)
    if (!value) return false
    sessionStorage.removeItem(LAUNCH_REFRESH_KEY)
    return true
  } catch {
    return false
  }
}

export function clientsPageCopy(opts: {
  fromLaunch: boolean
  hasCustomers: boolean
}): { title: string; lead: string } {
  if (opts.fromLaunch && !opts.hasCustomers) {
    return {
      title: 'Ajouter votre premier client',
      lead: 'Enregistrez les informations essentielles de votre client pour préparer vos devis et factures.',
    }
  }
  if (opts.fromLaunch) {
    return {
      title: 'Ajouter un client',
      lead: 'Enregistrez les informations essentielles de votre client pour préparer vos devis et factures.',
    }
  }
  return {
    title: 'Clients',
    lead: 'Fiches clients pour la facturation et le suivi commercial.',
  }
}

export function facturationPageCopy(opts: {
  fromLaunch: boolean
  hasInvoices: boolean
}): { formTitle: string; formLead: string } {
  if (opts.fromLaunch && !opts.hasInvoices) {
    return {
      formTitle: 'Créer votre première facture',
      formLead:
        'Sélectionnez un client, ajoutez vos prestations ou produits, puis vérifiez le document avant de l’enregistrer.',
    }
  }
  if (opts.fromLaunch) {
    return {
      formTitle: 'Créer une facture',
      formLead:
        'Sélectionnez un client, renseignez le montant HT, puis enregistrez la facture (brouillon).',
    }
  }
  return {
    formTitle: 'Créer un document',
    formLead: 'Créez devis et factures, suivez les encaissements et relances.',
  }
}

export function documentsPageCopy(opts: { fromLaunch: boolean }): {
  title: string
  lead: string
} {
  if (opts.fromLaunch) {
    return {
      title: 'Centralisez vos documents',
      lead: 'Importez une facture fournisseur, un justificatif ou un autre document professionnel. ComptaPilot le conservera dans votre espace documentaire.',
    }
  }
  return {
    title: 'Centre Documents',
    lead: 'Liste, filtres, aperçu Vault, puis enchaînement analyse → extraction → validation → proposition comptable.',
  }
}

type LaunchLike = {
  onboarding?: {
    steps?: Array<{ key: string; completed: boolean }>
    recommended_action?: {
      action_label: string
      action_path: string
    } | null
  }
} | null

export function customerSuccessActions(
  customer: { id: number; name: string },
  launch: LaunchLike,
): { primary: FirstExperienceAction; secondary: FirstExperienceAction[] } {
  const invoiceStep = launch?.onboarding?.steps?.find((s) => s.key === 'first_invoice')
  const invoiceDone = Boolean(invoiceStep?.completed)
  const reco = launch?.onboarding?.recommended_action

  let primary: FirstExperienceAction
  if (!invoiceDone) {
    primary = {
      label: 'Créer une facture pour ce client',
      to: invoicePathForCustomer(customer.id, true),
      tone: 'primary',
    }
  } else if (reco?.action_path) {
    primary = {
      label: reco.action_label,
      to: withLaunchSource(reco.action_path),
      tone: 'primary',
    }
  } else {
    primary = { label: 'Retourner au Dashboard', to: '/dashboard', tone: 'primary' }
  }

  return {
    primary,
    secondary: (
      [
        { label: 'Ajouter un autre client', to: withLaunchSource('/clients'), tone: 'secondary' },
        { label: 'Retourner au Dashboard', to: '/dashboard', tone: 'secondary' },
      ] as FirstExperienceAction[]
    ).filter((a) => a.to !== primary.to),
  }
}

export function invoiceSuccessActions(launch: LaunchLike): {
  primary: FirstExperienceAction
  secondary: FirstExperienceAction[]
} {
  const docStep = launch?.onboarding?.steps?.find((s) => s.key === 'first_document')
  const docDone = Boolean(docStep?.completed)
  const reco = launch?.onboarding?.recommended_action

  let primary: FirstExperienceAction
  if (!docDone) {
    primary = {
      label: 'Importer votre premier document',
      to: withLaunchSource('/documents'),
      tone: 'primary',
    }
  } else if (reco?.action_path) {
    primary = {
      label: reco.action_label,
      to: withLaunchSource(reco.action_path),
      tone: 'primary',
    }
  } else {
    primary = { label: 'Retourner au Dashboard', to: '/dashboard', tone: 'primary' }
  }

  return {
    primary,
    secondary: (
      [
        { label: 'Retourner au Dashboard', to: '/dashboard', tone: 'secondary' },
        { label: 'Importer un document', to: withLaunchSource('/documents'), tone: 'secondary' },
      ] as FirstExperienceAction[]
    ).filter((a) => a.to !== primary.to && a.label !== primary.label),
  }
}

export function documentSuccessActions(): {
  primary: FirstExperienceAction
  secondary: FirstExperienceAction[]
} {
  return {
    primary: { label: 'Retourner au Dashboard', to: '/dashboard', tone: 'primary' },
    secondary: [
      { label: 'Importer un autre document', to: withLaunchSource('/documents'), tone: 'secondary' },
    ],
  }
}

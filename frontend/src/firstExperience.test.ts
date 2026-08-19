import { createElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import FirstActionSuccessPanel from './components/FirstActionSuccessPanel'
import {
  clientsPageCopy,
  customerSuccessActions,
  documentSuccessActions,
  documentsPageCopy,
  facturationPageCopy,
  invoicePathForCustomer,
  invoiceSuccessActions,
  isLaunchDashboardSource,
  LAUNCH_REFRESH_KEY,
  LAUNCH_SOURCE,
  markLaunchDashboardStale,
  consumeLaunchDashboardStale,
  withLaunchSource,
} from './firstExperience'

describe('firstExperience helpers', () => {
  it('détecte source=launch-dashboard', () => {
    expect(isLaunchDashboardSource(LAUNCH_SOURCE)).toBe(true)
    expect(isLaunchDashboardSource(null)).toBe(false)
    expect(isLaunchDashboardSource('other')).toBe(false)
  })

  it('ajoute source sans casser le path', () => {
    expect(withLaunchSource('/clients')).toBe(`/clients?source=${LAUNCH_SOURCE}`)
    expect(withLaunchSource('/facturation?customer_id=3')).toContain('customer_id=3')
    expect(withLaunchSource('/facturation?customer_id=3')).toContain(`source=${LAUNCH_SOURCE}`)
    expect(withLaunchSource(`/clients?source=${LAUNCH_SOURCE}`)).toBe(
      `/clients?source=${LAUNCH_SOURCE}`,
    )
  })

  it('construit une route facture avec customer_id réel uniquement', () => {
    const path = invoicePathForCustomer(42)
    expect(path).toContain('customer_id=42')
    expect(path).not.toContain('{')
    expect(path).toContain(`source=${LAUNCH_SOURCE}`)
  })

  it('adapte les titres premier client / générique', () => {
    expect(clientsPageCopy({ fromLaunch: true, hasCustomers: false }).title).toMatch(/premier client/i)
    expect(clientsPageCopy({ fromLaunch: false, hasCustomers: false }).title).toBe('Clients')
    expect(clientsPageCopy({ fromLaunch: true, hasCustomers: true }).title).toBe('Ajouter un client')
  })

  it('adapte facture et documents', () => {
    expect(facturationPageCopy({ fromLaunch: true, hasInvoices: false }).formTitle).toMatch(
      /première facture/i,
    )
    expect(documentsPageCopy({ fromLaunch: true }).title).toMatch(/Centralisez/)
    expect(documentsPageCopy({ fromLaunch: false }).title).toMatch(/Centre Documents/)
  })

  it('recommande facture après client si étape incomplete', () => {
    const actions = customerSuccessActions(
      { id: 9, name: 'Acme' },
      {
        onboarding: {
          steps: [{ key: 'first_invoice', completed: false }],
          recommended_action: null,
        },
      },
    )
    expect(actions.primary.label).toMatch(/facture/i)
    expect(actions.primary.to).toContain('customer_id=9')
  })

  it('bascule sur la reco Launch si facture déjà faite', () => {
    const actions = customerSuccessActions(
      { id: 9, name: 'Acme' },
      {
        onboarding: {
          steps: [{ key: 'first_invoice', completed: true }],
          recommended_action: {
            action_label: 'Importer un document',
            action_path: '/documents',
          },
        },
      },
    )
    expect(actions.primary.label).toMatch(/document/i)
    expect(actions.primary.to).toContain('/documents')
  })

  it('recommande import document après facture', () => {
    const actions = invoiceSuccessActions({
      onboarding: {
        steps: [{ key: 'first_document', completed: false }],
        recommended_action: null,
      },
    })
    expect(actions.primary.to).toContain('/documents')
  })

  it('recommande retour dashboard après document', () => {
    expect(documentSuccessActions().primary.to).toBe('/dashboard')
  })

  it('marque et consomme le refresh Launch Dashboard', () => {
    sessionStorage.removeItem(LAUNCH_REFRESH_KEY)
    markLaunchDashboardStale()
    expect(sessionStorage.getItem(LAUNCH_REFRESH_KEY)).toBeTruthy()
    expect(consumeLaunchDashboardStale()).toBe(true)
    expect(consumeLaunchDashboardStale()).toBe(false)
  })
})

describe('FirstActionSuccessPanel', () => {
  it('annonce le succès et expose les actions', () => {
    const html = renderToStaticMarkup(
      createElement(
        MemoryRouter,
        null,
        createElement(FirstActionSuccessPanel, {
          title: 'Client ajouté',
          description: 'Le client est disponible :',
          resourceName: 'Acme',
          primaryAction: { label: 'Créer une facture', to: '/facturation?customer_id=1' },
          secondaryActions: [{ label: 'Retourner au Dashboard', to: '/dashboard', tone: 'secondary' }],
        }),
      ),
    )
    expect(html).toMatch(/aria-live="polite"/)
    expect(html).toMatch(/Client ajouté/)
    expect(html).toMatch(/Acme/)
    expect(html).toMatch(/href="\/facturation\?customer_id=1"/)
    expect(html).toMatch(/href="\/dashboard"/)
  })
})

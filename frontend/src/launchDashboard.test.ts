import { createElement, type ComponentProps } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import LaunchDashboard from './components/LaunchDashboard'
import {
  launchWelcomeLead,
  launchWelcomeTitle,
  type LaunchDashboardData,
} from './launchDashboard'

function sampleData(over: Partial<LaunchDashboardData> = {}): LaunchDashboardData {
  const base: LaunchDashboardData = {
    workspace_ready: true,
    user: { display_name: 'Chris' },
    organization: { name: 'CreaLab Auto' },
    onboarding: {
      completed_steps: 1,
      total_steps: 6,
      progress: 17,
      all_completed: false,
      recommended_action: {
        key: 'first_customer',
        title: 'Ajoutez votre premier client',
        description: 'Créez une fiche client pour préparer vos premiers devis et factures.',
        action_label: 'Ajouter un client',
        action_path: '/clients',
      },
      steps: [
        {
          key: 'company_setup',
          label: 'Configurer votre entreprise',
          completed: true,
        },
        {
          key: 'first_customer',
          label: 'Ajouter votre premier client',
          completed: false,
          action_label: 'Ajouter un client',
          action_path: '/clients',
        },
        {
          key: 'first_supplier',
          label: 'Ajouter votre premier fournisseur',
          completed: false,
        },
        {
          key: 'first_invoice',
          label: 'Créer votre première facture',
          completed: false,
          action_label: 'Créer une facture',
          action_path: '/facturation',
        },
        {
          key: 'first_document',
          label: 'Importer votre premier document',
          completed: false,
          action_label: 'Importer un document',
          action_path: '/documents',
        },
        {
          key: 'accounting_discovery',
          label: 'Découvrir votre espace comptable',
          completed: false,
          action_label: 'Ouvrir l’espace comptable',
          action_path: '/accounting',
        },
      ],
    },
    quick_actions: [
      {
        key: 'new_customer',
        label: 'Nouveau client',
        description: 'Créer une fiche client',
        path: '/clients',
        enabled: true,
      },
      {
        key: 'new_invoice',
        label: 'Nouvelle facture',
        description: 'Créer une facture',
        path: '/facturation',
        enabled: true,
      },
      {
        key: 'import_document',
        label: 'Importer un document',
        description: 'Ajouter un justificatif',
        path: '/documents',
        enabled: true,
      },
    ],
    recent_activity: [],
  }
  return { ...base, ...over, onboarding: { ...base.onboarding, ...(over.onboarding || {}) } }
}

function renderLaunch(props: Partial<ComponentProps<typeof LaunchDashboard>> = {}) {
  return renderToStaticMarkup(
    createElement(
      MemoryRouter,
      null,
      createElement(LaunchDashboard, {
        data: sampleData(),
        loading: false,
        error: '',
        onRetry: () => undefined,
        collapsed: false,
        onToggleCollapsed: () => undefined,
        ...props,
      }),
    ),
  )
}

describe('launchWelcome helpers', () => {
  it('affiche le prénom quand disponible', () => {
    expect(launchWelcomeTitle('Chris')).toBe('Bonjour Chris')
  })

  it('évite une formule incorrecte sans nom', () => {
    expect(launchWelcomeTitle(null)).toBe('Bienvenue dans ComptaPilot')
    expect(launchWelcomeTitle('   ')).toBe('Bienvenue dans ComptaPilot')
  })

  it('confirme que l’espace org est prêt', () => {
    expect(launchWelcomeLead('CreaLab Auto', true)).toBe('L’espace de CreaLab Auto est prêt.')
    expect(launchWelcomeLead('', false)).toMatch(/votre organisation/)
  })
})

describe('LaunchDashboard', () => {
  it('affiche un état de chargement annoncé', () => {
    const html = renderLaunch({ data: null, loading: true })
    expect(html).toMatch(/aria-busy="true"/)
    expect(html).toMatch(/aria-live="polite"/)
  })

  it('affiche bienvenue, org et progression', () => {
    const html = renderLaunch()
    expect(html).toMatch(/Bonjour Chris/)
    expect(html).toMatch(/CreaLab Auto/)
    expect(html).toMatch(/1 étapes terminées sur 6/)
    expect(html).toMatch(/role="progressbar"/)
    expect(html).toMatch(/aria-valuenow="17"/)
  })

  it('rend la checklist avec états terminée / à faire', () => {
    const html = renderLaunch()
    expect(html).toMatch(/Configurer votre entreprise/)
    expect(html).toMatch(/Terminée/)
    expect(html).toMatch(/À faire/)
    expect(html).toMatch(/Ajouter votre premier client/)
  })

  it('affiche l’action recommandée et navigue vers la route réelle', () => {
    const html = renderLaunch()
    expect(html).toMatch(/Ajoutez votre premier client/)
    expect(html).toMatch(/href="\/clients\?source=launch-dashboard"/)
    expect(html).toMatch(/Ajouter un client/)
  })

  it('affiche les actions rapides autorisées', () => {
    const html = renderLaunch()
    expect(html).toMatch(/Nouveau client/)
    expect(html).toMatch(/Nouvelle facture/)
    expect(html).toMatch(/Importer un document/)
    expect(html).toMatch(/href="\/facturation\?source=launch-dashboard"/)
    expect(html).toMatch(/href="\/documents\?source=launch-dashboard"/)
  })

  it('affiche un état vide pour l’activité récente', () => {
    const html = renderLaunch()
    expect(html).toMatch(/Aucune activité pour le moment/)
  })

  it('liste l’activité récente quand présente', () => {
    const html = renderLaunch({
      data: sampleData({
        recent_activity: [
          {
            id: 'inv-1',
            type: 'invoice_created',
            title: 'Facture créée',
            description: 'FAC-001',
            occurred_at: '2026-07-26T10:00:00Z',
            path: '/facturation',
          },
        ],
      }),
    })
    expect(html).toMatch(/Facture créée/)
    expect(html).toMatch(/FAC-001/)
  })

  it('affiche l’erreur API avec bouton Réessayer sans bloquer le schéma', () => {
    const onRetry = vi.fn()
    const html = renderLaunch({ data: null, loading: false, error: 'Service indisponible', onRetry })
    expect(html).toMatch(/Service indisponible/)
    expect(html).toMatch(/Réessayer|relancer|retry/i)
  })

  it('affiche progression 100 % et état démarrage terminé', () => {
    const html = renderLaunch({
      data: sampleData({
        onboarding: {
          completed_steps: 6,
          total_steps: 6,
          progress: 100,
          all_completed: true,
          recommended_action: null,
          steps: sampleData().onboarding.steps.map((s) => ({ ...s, completed: true })),
        },
      }),
    })
    expect(html).toMatch(/6 étapes terminées sur 6/)
    expect(html).toMatch(/aria-valuenow="100"/)
    expect(html).toMatch(/Démarrage terminé/)
  })

  it('réduit la checklist quand collapsed + all_completed', () => {
    const html = renderLaunch({
      collapsed: true,
      data: sampleData({
        onboarding: {
          ...sampleData().onboarding,
          completed_steps: 6,
          total_steps: 6,
          progress: 100,
          all_completed: true,
          recommended_action: null,
          steps: sampleData().onboarding.steps.map((s) => ({ ...s, completed: true })),
        },
      }),
    })
    expect(html).toMatch(/checklist masquée/)
    expect(html).not.toMatch(/Checklist de démarrage/)
  })

  it('structure responsive : grille launch-dashboard-grid', () => {
    const html = renderLaunch()
    expect(html).toMatch(/launch-dashboard-grid/)
    expect(html).toMatch(/launch-dashboard-main/)
    expect(html).toMatch(/launch-dashboard-side/)
  })

  it('gère l’absence de nom utilisateur', () => {
    const html = renderLaunch({
      data: sampleData({ user: { display_name: null } }),
    })
    expect(html).toMatch(/Bienvenue dans ComptaPilot/)
    expect(html).not.toMatch(/Bonjour null/)
  })
})

import { createElement, type ReactElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  Badge,
  Button,
  Container,
  EmptyState,
  FormField,
  FOUNDATION_CSS_VARS,
  Grid,
  Inline,
  Input,
  MetricCard,
  MOTION_DURATION,
  PageHeader,
  Progress,
  QuickActionCard,
  Section,
  SPACE_SCALE,
  Stack,
  StatCard,
} from './design-system'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')

function html(node: ReactElement) {
  return renderToStaticMarkup(node)
}

describe('E1.4 Component System', () => {
  it('Section expose titre, description et actions', () => {
    const out = html(
      createElement(
        Section,
        {
          title: 'Titre',
          description: 'Desc',
          actions: createElement(Button, null, 'Go'),
        },
        'contenu',
      ),
    )
    expect(out).toContain('Titre')
    expect(out).toContain('Desc')
    expect(out).toContain('Go')
    expect(out).toContain('ds-section__header')
    expect(out).toContain('ds-section__content')
  })

  it('StatCard sépare direction et sentiment', () => {
    const out = html(
      createElement(StatCard, {
        label: 'Dépenses',
        value: '1 200 €',
        trend: {
          value: '−8 %',
          direction: 'down',
          label: 'vs N-1',
          sentiment: 'positive',
        },
      }),
    )
    expect(out).toContain('Dépenses')
    expect(out).toContain('1 200 €')
    expect(out).toContain('ds-stat-card__trend--down')
    expect(out).toContain('ds-stat-card__trend--sentiment-positive')
  })

  it('StatCard loading et accent', () => {
    const loading = html(createElement(StatCard, { label: 'L', value: '0', loading: true }))
    expect(loading).toContain('aria-busy')
    const accent = html(
      createElement(StatCard, { label: 'A', value: '1', variant: 'accent' }),
    )
    expect(accent).toContain('ds-stat-card--accent')
  })

  it('MetricCard affiche progress/footer sans calcul', () => {
    const out = html(
      createElement(MetricCard, {
        title: 'Taux',
        value: '40 %',
        progress: 40,
        footer: 'Basé sur données fournies',
      }),
    )
    expect(out).toContain('Taux')
    expect(out).toContain('40 %')
    expect(out).toContain('Basé sur données fournies')
    expect(out).toContain('role="progressbar"')
  })

  it('QuickActionCard lien vs bouton vs disabled', () => {
    const link = html(
      createElement(QuickActionCard, {
        title: 'Ouvrir',
        href: 'https://example.com',
      }),
    )
    expect(link).toContain('<a ')
    expect(link).toContain('https://example.com')

    const btn = html(
      createElement(QuickActionCard, {
        title: 'Cliquer',
        onClick: () => undefined,
      }),
    )
    expect(btn).toContain('<button')

    const disabled = html(
      createElement(QuickActionCard, {
        title: 'Bloqué',
        disabled: true,
        disabledReason: 'Bientôt',
        onClick: () => undefined,
      }),
    )
    expect(disabled).toContain('disabled')
    expect(disabled).toContain('Bientôt')
  })

  it('Container / Stack / Inline / Grid', () => {
    expect(html(createElement(Container, { size: 'sm' }, 'x'))).toContain('ds-container--sm')
    expect(html(createElement(Container, { padding: 'lg' }, 'x'))).toContain('ds-container--pad-lg')

    const stack = html(
      createElement(Stack, { gap: 6, as: 'ul' }, createElement('li', null, 'a')),
    )
    expect(stack.startsWith('<ul')).toBe(true)
    expect(stack).toContain('--space-6')

    const inline = html(
      createElement(Inline, { wrap: true, align: 'center' }, 'a'),
    )
    expect(inline).toContain('ds-inline--wrap')
    expect(inline).toContain('ds-inline--align-center')

    const grid = html(
      createElement(Grid, { columns: 'auto-fit', minItemWidth: '12rem' }, 'c'),
    )
    expect(grid).toContain('ds-grid--auto-fit')
    expect(html(createElement(Grid, { columns: 3, responsive: true }, 'c'))).toContain(
      'ds-grid--cols-3',
    )
  })

  it('FormField / Input / Button / PageHeader / EmptyState / Progress / Badge', () => {
    expect(html(createElement(Button, { variant: 'secondary' }, 'Ok'))).toContain('secondary')
    expect(html(createElement(Input, { id: 'i1', defaultValue: 'v' }))).toContain('ds-input')
    expect(
      html(
        createElement(FormField, { label: 'Nom', htmlFor: 'n1', error: 'Erreur' }, 'child'),
      ),
    ).toContain('Erreur')
    const wired = html(
      createElement(
        FormField,
        { label: 'Email', htmlFor: 'email1', error: 'Requis' },
        createElement(Input, { id: 'email1' }),
      ),
    )
    expect(wired).toContain('aria-describedby="email1-error"')
    expect(wired).toContain('aria-invalid="true"')
    expect(wired).toContain('id="email1-error"')
    expect(html(createElement(PageHeader, { title: 'Page' }))).toContain('ds-page-header')
    expect(html(createElement(EmptyState, { title: 'Vide' }))).toContain('Vide')
    expect(html(createElement(Progress, { value: 50 }))).toContain('50 %')
    expect(html(createElement(Badge, { tone: 'accent' }, 'A'))).toContain('ds-badge--accent')
    expect(html(createElement(Badge, { tone: 'danger' }, 'D'))).toContain('ds-badge--danger')
  })

  it('motion + foundation tokens présents', () => {
    expect(MOTION_DURATION.fast).toBe('140ms')
    expect(SPACE_SCALE[4]).toBe('1rem')
    expect(FOUNDATION_CSS_VARS.motionDuration.fast).toBe('--motion-duration-fast')

    const cssRoot = readFileSync(join(root, 'src/index.css'), 'utf8')
    expect(cssRoot).toContain('--motion-duration-fast:')
    expect(cssRoot).toContain('--space-4:')
    expect(cssRoot).toContain('--radius-lg:')
    expect(cssRoot).toContain('--shadow-md:')
    expect(cssRoot).toContain('--container-lg:')

    const compCss = readFileSync(
      join(root, 'src/design-system/components/components.css'),
      'utf8',
    )
    expect(compCss).toContain('prefers-reduced-motion')
    expect(compCss).toContain('transition: none')
    expect(compCss).toContain('.ds-input:focus-visible')
  })

  it('composants sans Product Registry / fetch', () => {
    const files = [
      'Section.tsx',
      'StatCard.tsx',
      'MetricCard.tsx',
      'QuickActionCard.tsx',
      'Container.tsx',
      'Stack.tsx',
      'Inline.tsx',
      'Grid.tsx',
      'Button.tsx',
      'FormField.tsx',
    ]
    for (const file of files) {
      const src = readFileSync(join(root, 'src/design-system/components', file), 'utf8')
      expect(src).not.toMatch(/products\/registry|getProductById|fetch\(|api\./)
    }
  })

  it('Dialog non livré — report E1.4.1 documenté', () => {
    const files = readFileSync(
      join(root, 'src/design-system/components/index.ts'),
      'utf8',
    )
    expect(files).not.toMatch(/Dialog/)
    const doc = readFileSync(
      join(root, 'docs/design-system-component-system-v1.md'),
      'utf8',
    )
    expect(doc).toContain('E1.4.1')
    expect(doc).toContain('window.confirm')
  })
})

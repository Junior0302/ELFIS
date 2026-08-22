/**
 * Helpers partagés — parcours Composer guidé (tests facturation).
 * Aligné sur COMPOSER_GUIDED_STEPS.items.title du produit.
 */
import { expect } from 'vitest'
import { screen, within } from '@testing-library/react'
import type userEvent from '@testing-library/user-event'

/** Titre d’étape items du composer guidé (F1.3.2). */
export const COMPOSER_PRODUCTS_STEP_HEADING = /Quels produits et services/i

export async function expectComposerProductsStep(): Promise<void> {
  expect(
    await screen.findByRole('heading', { name: COMPOSER_PRODUCTS_STEP_HEADING }),
  ).toBeInTheDocument()
}

export async function goToComposerProductsStep(
  user: ReturnType<typeof userEvent.setup>,
): Promise<void> {
  await user.click(await screen.findByRole('button', { name: /\+ Ajouter un client/i }))
  await user.type(screen.getByLabelText(/Nom du nouveau client/i), 'Dupont SAS')
  const panel = screen.getByLabelText(/Nom du nouveau client/i).closest('.ps-picker__actions') as HTMLElement
  await user.click(within(panel).getByRole('button', { name: 'Enregistrer' }))
  await user.click(screen.getByRole('button', { name: 'Continuer' }))
  await expectComposerProductsStep()
}

function structuredPreviewTotals(): Element | null {
  return document.querySelector('[data-live-preview="structured"] [data-dds-block="totals"]')
}

export function expectZeroSubtotalHt(): void {
  const block = structuredPreviewTotals()
  expect(block?.textContent).toMatch(/Total HT[\s\S]*0/)
}

export function expectZeroTotalTtc(): void {
  const block = structuredPreviewTotals()
  expect(block?.textContent).toMatch(/Total TTC[\s\S]*0/)
}

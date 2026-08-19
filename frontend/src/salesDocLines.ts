/** Lignes devis/facture — alignées sur le schéma BE / sales_pdf. */

export type SalesLineDraft = {
  label: string
  quantity: number
  unit_price: number
  catalog_item_id?: number | null
}

export function emptySalesLine(): SalesLineDraft {
  return { label: '', quantity: 1, unit_price: 0, catalog_item_id: null }
}

export function lineAmountHt(line: SalesLineDraft): number {
  const qty = Number(line.quantity) || 0
  const price = Number(line.unit_price) || 0
  return Math.round(qty * price * 100) / 100
}

export function linesTotalHt(lines: SalesLineDraft[]): number {
  return Math.round(lines.reduce((sum, line) => sum + lineAmountHt(line), 0) * 100) / 100
}

export function normalizeSalesLines(lines: SalesLineDraft[]): SalesLineDraft[] {
  return lines
    .map((line) => ({
      label: (line.label || '').trim(),
      quantity: Number(line.quantity) || 0,
      unit_price: Number(line.unit_price) || 0,
      catalog_item_id: line.catalog_item_id ?? null,
    }))
    .filter((line) => line.label.length > 0)
}

export function salesLinesFromDoc(
  lines: Array<{ label?: string; quantity?: number; unit_price?: number; catalog_item_id?: number | null }> | undefined,
  fallbackHt: number,
): SalesLineDraft[] {
  if (lines && lines.length > 0) {
    return lines.map((line) => ({
      label: line.label || '',
      quantity: Number(line.quantity) || 1,
      unit_price: Number(line.unit_price) || 0,
      catalog_item_id: line.catalog_item_id ?? null,
    }))
  }
  if (fallbackHt > 0) {
    return [{ label: 'Prestation', quantity: 1, unit_price: fallbackHt, catalog_item_id: null }]
  }
  return [emptySalesLine()]
}

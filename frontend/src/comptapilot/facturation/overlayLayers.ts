/**
 * Z-index tokens — flux création document / sous-modales (F1.3.2.2).
 * Hiérarchie intentionnelle (pas de valeurs magiques dispersées).
 */

export const FP_OVERLAY_Z = {
  documents: 0,
  composerBackdrop: 1000,
  composerDialog: 1010,
  submodalBackdrop: 1020,
  catalogModal: 1030,
  nestedCreate: 1040,
} as const

export type FpOverlayZKey = keyof typeof FP_OVERLAY_Z

/** CSS custom properties (miroir). */
export const FP_OVERLAY_Z_CSS = {
  documents: '--fp-z-documents',
  composerBackdrop: '--fp-z-composer-backdrop',
  composerDialog: '--fp-z-composer-dialog',
  submodalBackdrop: '--fp-z-submodal-backdrop',
  catalogModal: '--fp-z-catalog-modal',
  nestedCreate: '--fp-z-nested-create',
} as const

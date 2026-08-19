/**
 * Map ProductTheme → CSS variables + DOM data attributes.
 */

import { tokensToCssVariables, THEME_DOM_ATTR, type PilotCssVarName } from './cssVariables'
import type { ProductTheme, ThemeDomAttributes } from './interfaces'

export function themeToCssVariables(theme: ProductTheme): Record<PilotCssVarName, string> {
  return tokensToCssVariables(theme.tokens)
}

export function themeToDomAttributes(theme: ProductTheme): ThemeDomAttributes {
  return {
    [THEME_DOM_ATTR.product]: theme.productId,
    [THEME_DOM_ATTR.theme]: `${theme.productId}-${theme.colorScheme}`,
    [THEME_DOM_ATTR.colorScheme]: theme.colorScheme,
  }
}

export { tokensToCssVariables, THEME_DOM_ATTR, PILOT_CSS_VAR_NAMES, PILOT_CSS_VAR_BY_TOKEN } from './cssVariables'

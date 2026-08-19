/**
 * Foundation tokens — spacing, radius, shadow, motion, container, controls.
 * Values aligned with legacy ComptaPilot UI for visual parity.
 */

export const SPACE_SCALE = {
  1: '0.25rem', // 4
  2: '0.5rem', // 8
  3: '0.75rem', // 12
  4: '1rem', // 16
  5: '1.25rem', // 20
  6: '1.5rem', // 24
  8: '2rem', // 32
  10: '2.5rem', // 40
  12: '3rem', // 48
} as const

export type SpaceToken = keyof typeof SPACE_SCALE

export const RADIUS_SCALE = {
  sm: '8px',
  md: '12px',
  lg: '18px', // legacy --radius
  xl: '28px',
  pill: '999px',
} as const

export type RadiusToken = keyof typeof RADIUS_SCALE

export const SHADOW_SCALE = {
  sm: '0 4px 12px rgba(7, 40, 30, 0.06)',
  md: '0 18px 50px rgba(7, 40, 30, 0.08)', // legacy --shadow
  lg: '0 24px 60px rgba(8, 24, 18, 0.28)',
} as const

export type ShadowToken = keyof typeof SHADOW_SCALE

export const CONTAINER_SCALE = {
  sm: '40rem', // 640
  md: '48rem', // 768
  lg: '64rem', // 1024
  xl: '75rem', // 1200
  full: '100%',
} as const

export type ContainerSize = keyof typeof CONTAINER_SCALE

export const CONTROL_HEIGHT = {
  sm: '2rem',
  md: '2.75rem',
  lg: '3.25rem',
} as const

export type ControlHeight = keyof typeof CONTROL_HEIGHT

export const MOTION_DURATION = {
  instant: '0ms',
  fast: '140ms',
  normal: '220ms',
  slow: '340ms',
} as const

export type MotionDuration = keyof typeof MOTION_DURATION

export const MOTION_EASING = {
  standard: 'cubic-bezier(0.22, 1, 0.36, 1)',
  emphasized: 'cubic-bezier(0.2, 0, 0, 1)',
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
} as const

export type MotionEasing = keyof typeof MOTION_EASING

/** CSS custom property names for foundation tokens. */
export const FOUNDATION_CSS_VARS = {
  space: {
    1: '--space-1',
    2: '--space-2',
    3: '--space-3',
    4: '--space-4',
    5: '--space-5',
    6: '--space-6',
    8: '--space-8',
    10: '--space-10',
    12: '--space-12',
  },
  radius: {
    sm: '--radius-sm',
    md: '--radius-md',
    lg: '--radius-lg',
    xl: '--radius-xl',
    pill: '--radius-pill',
  },
  shadow: {
    sm: '--shadow-sm',
    md: '--shadow-md',
    lg: '--shadow-lg',
  },
  container: {
    sm: '--container-sm',
    md: '--container-md',
    lg: '--container-lg',
    xl: '--container-xl',
  },
  control: {
    sm: '--control-height-sm',
    md: '--control-height-md',
    lg: '--control-height-lg',
  },
  motionDuration: {
    instant: '--motion-duration-instant',
    fast: '--motion-duration-fast',
    normal: '--motion-duration-normal',
    slow: '--motion-duration-slow',
  },
  motionEasing: {
    standard: '--motion-easing-standard',
    emphasized: '--motion-easing-emphasized',
    exit: '--motion-easing-exit',
  },
} as const

export type GapToken = SpaceToken

export function spaceVar(token: SpaceToken): string {
  return `var(${FOUNDATION_CSS_VARS.space[token]})`
}

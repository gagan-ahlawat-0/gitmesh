/**
 * Animation Utilities for Framer Motion
 *
 * Common animation variants and helpers to use with SafeAnimatePresence
 */

import type { Variants } from 'framer-motion';

/**
 * Fade animation variants
 */
export const fadeVariants: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

/**
 * Slide up animation variants
 */
export const slideUpVariants: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

/**
 * Slide down animation variants
 */
export const slideDownVariants: Variants = {
  initial: { opacity: 0, y: -20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 20 },
};

/**
 * Scale animation variants
 */
export const scaleVariants: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.95 },
};

/**
 * Slide from left variants
 */
export const slideLeftVariants: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 },
};

/**
 * Slide from right variants
 */
export const slideRightVariants: Variants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 },
};

/**
 * Modal/Dialog animation variants
 */
export const modalVariants: Variants = {
  initial: { opacity: 0, scale: 0.9, y: 20 },
  animate: { opacity: 1, scale: 1, y: 0 },
  exit: { opacity: 0, scale: 0.9, y: 20 },
};

/**
 * Collapse/Expand animation variants
 */
export const collapseVariants: Variants = {
  initial: { height: 0, opacity: 0 },
  animate: { height: 'auto', opacity: 1 },
  exit: { height: 0, opacity: 0 },
};

/**
 * Standard transition configuration
 */
export const standardTransition = {
  duration: 0.2,
  ease: [0.4, 0.0, 0.2, 1], // cubic-bezier
};

/**
 * Fast transition configuration
 */
export const fastTransition = {
  duration: 0.15,
  ease: [0.4, 0.0, 0.2, 1],
};

/**
 * Slow transition configuration
 */
export const slowTransition = {
  duration: 0.3,
  ease: [0.4, 0.0, 0.2, 1],
};

/**
 * Spring transition configuration
 */
export const springTransition = {
  type: 'spring',
  stiffness: 300,
  damping: 30,
};

/**
 * Helper to create a safe key for AnimatePresence
 * Ensures unique keys for conditionally rendered components
 */
export function createAnimationKey(base: string, condition: boolean | string | number): string {
  return `${base}-${String(condition)}`;
}

/**
 * Helper to combine variants with custom overrides
 */
export function combineVariants(base: Variants, overrides: Partial<Variants>): Variants {
  return Object.assign({}, base, overrides) as Variants;
}

/**
 * Preset: Route transition variants
 * Use with SafeAnimatePresence mode="wait"
 */
export const routeTransitionVariants: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: standardTransition },
  exit: { opacity: 0, y: -20, transition: standardTransition },
};

/**
 * Preset: Notification variants
 */
export const notificationVariants: Variants = {
  initial: { opacity: 0, y: -20, scale: 0.95 },
  animate: { opacity: 1, y: 0, scale: 1, transition: fastTransition },
  exit: { opacity: 0, y: -20, scale: 0.95, transition: fastTransition },
};

/**
 * Preset: Dropdown menu variants
 */
export const dropdownVariants: Variants = {
  initial: { opacity: 0, y: -10, scale: 0.95 },
  animate: { opacity: 1, y: 0, scale: 1, transition: fastTransition },
  exit: { opacity: 0, y: -10, scale: 0.95, transition: fastTransition },
};

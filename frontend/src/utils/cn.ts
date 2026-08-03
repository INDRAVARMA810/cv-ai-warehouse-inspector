import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Compose class names, resolving Tailwind conflicts.
 *
 * Lets a component define sensible defaults that a caller can still
 * override via `className` without fighting specificity.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a monetary amount. Whole numbers are shown without decimals (e.g. "1,517,323"),
 * non-whole numbers are shown with exactly 2 decimal places (e.g. "1,517,323.50").
 */
export function formatMoney(amount: number): string {
  const hasDecimals = amount % 1 !== 0
  return amount.toLocaleString('en-US', {
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: hasDecimals ? 2 : 0,
  })
}

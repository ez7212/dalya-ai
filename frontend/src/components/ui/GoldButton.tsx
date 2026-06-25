import Link from 'next/link'
import { cn } from '@/lib/utils'

interface ButtonProps {
  children: React.ReactNode
  href?: string
  onClick?: () => void
  className?: string
  size?: 'sm' | 'md'
}

// Name kept for import compatibility, but the gold theme is retired — this now renders the
// current slate brand CTA used across the app. New code should prefer bg-brand-600 directly.
export function GoldButton({ children, href, onClick, className, size = 'md' }: ButtonProps) {
  const cls = cn(
    'inline-flex items-center justify-center rounded-md tracking-wide uppercase font-semibold transition-colors',
    'bg-[var(--color-brand-600,#324B6B)] text-white hover:bg-[var(--color-brand-500,#3D5A80)]',
    'focus-visible:ring-2 focus-visible:ring-[var(--color-brand-500,#3D5A80)]/50 focus-visible:outline-none',
    size === 'sm' ? 'px-5 py-2.5 text-sm' : 'px-8 py-4 text-sm',
    className
  )
  if (href) return <Link href={href} className={cls}>{children}</Link>
  return <button onClick={onClick} className={cls}>{children}</button>
}

import Link from 'next/link'
import { cn } from '@/lib/utils'

interface ButtonProps {
  children: React.ReactNode
  href?: string
  onClick?: () => void
  className?: string
  size?: 'sm' | 'md'
}

export function GhostButton({ children, href, onClick, className, size = 'md' }: ButtonProps) {
  const cls = cn(
    'btn-ghost rounded-md tracking-wide uppercase font-semibold focus-visible:ring-2 focus-visible:ring-gold/50 focus-visible:outline-none',
    size === 'sm' ? 'px-5 py-2.5 text-sm' : 'px-8 py-4 text-sm',
    className
  )
  if (href) return <Link href={href} className={cls}>{children}</Link>
  return <button onClick={onClick} className={cls}>{children}</button>
}

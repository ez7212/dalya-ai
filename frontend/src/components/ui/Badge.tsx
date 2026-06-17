import { cn } from '@/lib/utils'

type BadgeVariant = 'verified' | 'sage' | 'copper'

interface BadgeProps {
  variant: BadgeVariant
  children: React.ReactNode
  className?: string
  icon?: string
}

export function Badge({ variant, children, className, icon }: BadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded',
      variant === 'verified' && 'badge-verified',
      variant === 'sage' && 'badge-sage',
      variant === 'copper' && 'border border-copper/40 text-copper bg-copper/10',
      className
    )}>
      {icon && <span className="material-symbols-outlined" style={{ fontSize: '11px' }}>{icon}</span>}
      {children}
    </span>
  )
}

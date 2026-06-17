interface ProgressBarProps {
  percent: number
  variant?: 'gold' | 'copper'
}

export function ProgressBar({ percent, variant = 'gold' }: ProgressBarProps) {
  return (
    <div
      className="progress-bar h-1.5 w-full"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`${percent}% payment complete`}
    >
      <div
        className={variant === 'copper' ? 'progress-fill-copper' : 'progress-fill'}
        style={{ width: `${percent}%` }}
      />
    </div>
  )
}

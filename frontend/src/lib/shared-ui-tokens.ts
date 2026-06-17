export const sharedUi = {
  shell: 'bg-surface-0 text-text-1 font-sans',
  panel: 'rounded border border-neutral-200 bg-white shadow-[0_1px_2px_rgba(22,22,19,0.04)]',
  inset: 'rounded border border-neutral-200 bg-neutral-50',
  label: 'text-[11px] font-semibold uppercase tracking-[0.12em] text-text-3',
  heading: 'text-base font-semibold text-neutral-800',
  body: 'text-sm leading-relaxed text-text-2',
  muted: 'text-xs leading-relaxed text-text-3',
  primaryButton:
    'inline-flex min-h-11 items-center justify-center gap-2 rounded bg-brand-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50',
  secondaryButton:
    'inline-flex min-h-11 items-center justify-center gap-2 rounded border border-neutral-300 bg-white px-4 py-2.5 text-sm font-medium text-text-1 transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-50',
  iconButton:
    'inline-flex h-11 w-11 items-center justify-center rounded border border-neutral-300 bg-white text-text-2 transition-colors hover:bg-neutral-100 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-50',
  textInput:
    'w-full rounded border border-neutral-300 bg-white px-3 py-2.5 text-sm text-text-1 placeholder:text-text-3 outline-none transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20',
  chip:
    'inline-flex items-center gap-1 rounded border border-neutral-200 bg-white px-2 py-1 text-[11px] font-medium text-text-2',
  mono: 'font-mono text-[12px] tabular-nums',
}

export const unitProfileLabels: Record<string, string> = {
  layout: 'Layout',
  condition: 'Condition',
  view: 'View',
  building_community_quirks: 'Building quirks',
  ac_utilities: 'AC and utilities',
  parking: 'Parking',
  neighbor_situation: 'Neighbor situation',
  agent_subjective_notes: 'Subjective notes',
}

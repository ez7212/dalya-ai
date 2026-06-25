export type StatusFilter = 'all' | 'live' | 'draft' | 'ready' | 'off_plan'
export type AttentionFilter = 'all' | 'attention' | 'buyers' | 'offers' | 'viewings' | 'recent'
export type InventorySort = 'last_activity' | 'created' | 'buyers' | 'offers' | 'viewings' | 'price'
export type InventoryDisplayMode = 'grid' | 'table'

interface AgentListingsControlsProps {
  readonly totalCount: number
  readonly visibleCount: number
  readonly search: string
  readonly statusFilter: StatusFilter
  readonly attentionFilter: AttentionFilter
  readonly sort: InventorySort
  readonly view: InventoryDisplayMode
  readonly onSearchChange: (value: string) => void
  readonly onStatusFilterChange: (value: StatusFilter) => void
  readonly onAttentionFilterChange: (value: AttentionFilter) => void
  readonly onSortChange: (value: InventorySort) => void
  readonly onViewChange: (value: InventoryDisplayMode) => void
}

const STATUS_FILTERS: readonly { readonly value: StatusFilter; readonly label: string }[] = [
  { value: 'all', label: 'All inventory' },
  { value: 'live', label: 'Live' },
  { value: 'draft', label: 'Draft' },
  { value: 'ready', label: 'Ready' },
  { value: 'off_plan', label: 'Off-plan' },
]

const ATTENTION_FILTERS: readonly { readonly value: AttentionFilter; readonly label: string }[] = [
  { value: 'all', label: 'All work' },
  { value: 'attention', label: 'Attention needed' },
  { value: 'buyers', label: 'Active buyers' },
  { value: 'offers', label: 'Open offers' },
  { value: 'viewings', label: 'Active viewings' },
  { value: 'recent', label: 'Recent activity' },
]

const SORT_OPTIONS: readonly { readonly value: InventorySort; readonly label: string }[] = [
  { value: 'last_activity', label: 'Last activity' },
  { value: 'created', label: 'Created date' },
  { value: 'buyers', label: 'Buyer conversations' },
  { value: 'offers', label: 'Open offers' },
  { value: 'viewings', label: 'Active viewings' },
  { value: 'price', label: 'Asking price' },
]

export function AgentListingsControls({
  totalCount,
  visibleCount,
  search,
  statusFilter,
  attentionFilter,
  sort,
  view,
  onSearchChange,
  onStatusFilterChange,
  onAttentionFilterChange,
  onSortChange,
  onViewChange,
}: AgentListingsControlsProps) {
  return (
    <div className="border-b border-neutral-200 px-4 py-4 sm:px-5">
      <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_minmax(180px,220px)_minmax(200px,260px)_minmax(180px,220px)]">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">Search</span>
          <span className="mt-1 flex h-10 items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-500/20">
            <span className="material-symbols-outlined text-[18px] text-neutral-500" aria-hidden="true">search</span>
            <input
              type="search"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Title, community, unit, listing id"
              className="min-w-0 flex-1 bg-transparent text-sm text-neutral-900 outline-none placeholder:text-neutral-400"
            />
          </span>
        </label>

        <FilterSelect
          label="Status"
          value={statusFilter}
          options={STATUS_FILTERS}
          onChange={(value) => onStatusFilterChange(parseStatusFilter(value))}
        />
        <FilterSelect
          label="Work"
          value={attentionFilter}
          options={ATTENTION_FILTERS}
          onChange={(value) => onAttentionFilterChange(parseAttentionFilter(value))}
        />
        <FilterSelect label="Sort" value={sort} options={SORT_OPTIONS} onChange={(value) => onSortChange(parseInventorySort(value))} />
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-xs text-neutral-500">
          Showing <span className="font-semibold tabular-nums text-neutral-700">{visibleCount}</span> of{' '}
          <span className="font-semibold tabular-nums text-neutral-700">{totalCount}</span> listings
        </p>
        <ViewToggle view={view} onViewChange={onViewChange} />
      </div>
    </div>
  )
}

function ViewToggle({ view, onViewChange }: { readonly view: InventoryDisplayMode; readonly onViewChange: (value: InventoryDisplayMode) => void }) {
  return (
    <div className="inline-flex rounded-md border border-neutral-300 bg-white p-0.5" role="group" aria-label="View mode">
      <ViewToggleButton active={view === 'grid'} onClick={() => onViewChange('grid')} icon="grid_view" label="Grid" />
      <ViewToggleButton active={view === 'table'} onClick={() => onViewChange('table')} icon="table_rows" label="Table" />
    </div>
  )
}

function ViewToggleButton({
  active,
  onClick,
  icon,
  label,
}: {
  readonly active: boolean
  readonly onClick: () => void
  readonly icon: string
  readonly label: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`inline-flex h-8 items-center gap-1.5 rounded-[5px] px-2.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30 ${
        active ? 'bg-brand-50 text-brand-700' : 'text-neutral-600 hover:bg-neutral-50'
      }`}
    >
      <span className="material-symbols-outlined text-[18px]" aria-hidden="true">{icon}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  readonly label: string
  readonly value: string
  readonly options: readonly { readonly value: string; readonly label: string }[]
  readonly onChange: (value: string) => void
}) {
  return (
    <label className="block">
      <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm font-medium text-neutral-800 outline-none transition-colors hover:bg-neutral-50 focus:border-brand-300 focus:ring-2 focus:ring-brand-500/20"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function parseStatusFilter(value: string): StatusFilter {
  switch (value) {
    case 'live':
    case 'draft':
    case 'ready':
    case 'off_plan':
      return value
    default:
      return 'all'
  }
}

function parseAttentionFilter(value: string): AttentionFilter {
  switch (value) {
    case 'attention':
    case 'buyers':
    case 'offers':
    case 'viewings':
    case 'recent':
      return value
    default:
      return 'all'
  }
}

function parseInventorySort(value: string): InventorySort {
  switch (value) {
    case 'created':
    case 'buyers':
    case 'offers':
    case 'viewings':
    case 'price':
      return value
    default:
      return 'last_activity'
  }
}

'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import { apiFetch, BROKERAGE_CONTEXT_FORBIDDEN_EVENT, BROKERAGE_CONTEXT_REQUIRED_EVENT, getStoredBrokerageId, setStoredBrokerageId } from '@/lib/api'
import { useAuth } from '@/components/providers/AuthProvider'

export interface ActiveBrokerage {
  brokerage_id: string
  name: string
  role: string
  membership_id: string
}

interface BrokerageInventory {
  active_brokerages: ActiveBrokerage[]
  requires_selection: boolean
  default_brokerage_id: string | null
}

type BrokerageStatus = 'idle' | 'loading' | 'ready' | 'selection_required' | 'no_membership' | 'error'

interface BrokerageContextValue {
  activeBrokerages: ActiveBrokerage[]
  selectedBrokerageId: string | null
  selectedBrokerage: ActiveBrokerage | null
  status: BrokerageStatus
  errorMessage: string | null
  selectBrokerage: (brokerageId: string) => void
  clearSelection: () => void
  refreshBrokerages: () => Promise<void>
}

const BrokerageContext = createContext<BrokerageContextValue | null>(null)

export function useBrokerageContext() {
  const context = useContext(BrokerageContext)
  if (!context) {
    throw new Error('useBrokerageContext must be used inside BrokerageProvider')
  }
  return context
}

export function BrokerageProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth()
  const queryClient = useQueryClient()
  const [activeBrokerages, setActiveBrokerages] = useState<ActiveBrokerage[]>([])
  const [selectedBrokerageId, setSelectedBrokerageId] = useState<string | null>(null)
  const [status, setStatus] = useState<BrokerageStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const applyInventory = useCallback((inventory: BrokerageInventory) => {
    const brokerages = inventory.active_brokerages
    setActiveBrokerages(brokerages)
    setErrorMessage(null)

    if (brokerages.length === 0) {
      setStoredBrokerageId(null)
      setSelectedBrokerageId(null)
      setStatus('no_membership')
      return
    }

    if (brokerages.length === 1) {
      const brokerageId = brokerages[0].brokerage_id
      if (getStoredBrokerageId() !== brokerageId) {
        queryClient.clear()
      }
      setStoredBrokerageId(brokerageId)
      setSelectedBrokerageId(brokerageId)
      setStatus('ready')
      return
    }

    const storedBrokerageId = getStoredBrokerageId()
    const storedIsValid = Boolean(
      storedBrokerageId && brokerages.some((brokerage) => brokerage.brokerage_id === storedBrokerageId)
    )

    if (storedIsValid) {
      setSelectedBrokerageId(storedBrokerageId)
      setStatus('ready')
      return
    }

    setStoredBrokerageId(null)
    setSelectedBrokerageId(null)
    setStatus('selection_required')
  }, [queryClient])

  const refreshBrokerages = useCallback(async () => {
    if (!user) {
      setActiveBrokerages([])
      setSelectedBrokerageId(null)
      setStatus('idle')
      return
    }

    setStatus((current) => current === 'ready' ? current : 'loading')
    try {
      const response = await apiFetch('/api/v1/me/brokerages')
      if (!response.ok) {
        throw new Error(`Membership lookup returned ${response.status}`)
      }
      const inventory = await response.json() as BrokerageInventory
      applyInventory(inventory)
    } catch (error) {
      setStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Could not load brokerage memberships.')
    }
  }, [applyInventory, user])

  useEffect(() => {
    if (authLoading) return
    void refreshBrokerages()
  }, [authLoading, refreshBrokerages])

  useEffect(() => {
    const handleRequired = () => {
      setStatus('selection_required')
    }
    const handleForbidden = () => {
      setSelectedBrokerageId(null)
      setStatus('selection_required')
      void refreshBrokerages()
    }

    window.addEventListener(BROKERAGE_CONTEXT_REQUIRED_EVENT, handleRequired)
    window.addEventListener(BROKERAGE_CONTEXT_FORBIDDEN_EVENT, handleForbidden)
    return () => {
      window.removeEventListener(BROKERAGE_CONTEXT_REQUIRED_EVENT, handleRequired)
      window.removeEventListener(BROKERAGE_CONTEXT_FORBIDDEN_EVENT, handleForbidden)
    }
  }, [refreshBrokerages])

  const selectBrokerage = useCallback((brokerageId: string) => {
    const brokerage = activeBrokerages.find((item) => item.brokerage_id === brokerageId)
    if (!brokerage) {
      setStoredBrokerageId(null)
      setSelectedBrokerageId(null)
      queryClient.clear()
      setStatus(activeBrokerages.length > 0 ? 'selection_required' : 'no_membership')
      return
    }

    if (selectedBrokerageId !== brokerage.brokerage_id) {
      queryClient.clear()
    }
    setStoredBrokerageId(brokerage.brokerage_id)
    setSelectedBrokerageId(brokerage.brokerage_id)
    setStatus('ready')
  }, [activeBrokerages, queryClient, selectedBrokerageId])

  const clearSelection = useCallback(() => {
    setStoredBrokerageId(null)
    setSelectedBrokerageId(null)
    queryClient.clear()
    setStatus(activeBrokerages.length > 1 ? 'selection_required' : activeBrokerages.length === 0 ? 'no_membership' : 'ready')
  }, [activeBrokerages.length, queryClient])

  const selectedBrokerage = useMemo(
    () => activeBrokerages.find((brokerage) => brokerage.brokerage_id === selectedBrokerageId) ?? null,
    [activeBrokerages, selectedBrokerageId]
  )

  const value = useMemo<BrokerageContextValue>(() => ({
    activeBrokerages,
    selectedBrokerageId,
    selectedBrokerage,
    status,
    errorMessage,
    selectBrokerage,
    clearSelection,
    refreshBrokerages,
  }), [
    activeBrokerages,
    selectedBrokerageId,
    selectedBrokerage,
    status,
    errorMessage,
    selectBrokerage,
    clearSelection,
    refreshBrokerages,
  ])

  return (
    <BrokerageContext.Provider value={value}>
      {children}
    </BrokerageContext.Provider>
  )
}

export function BrokerageSelector() {
  const {
    activeBrokerages,
    selectedBrokerageId,
    selectedBrokerage,
    status,
    selectBrokerage,
  } = useBrokerageContext()

  if (status === 'loading' || status === 'idle') {
    return <div className="h-9 w-44 animate-pulse rounded-md bg-neutral-100" aria-label="Loading brokerage context" />
  }

  if (status === 'no_membership') {
    return (
      <Link href="/onboarding/agent" className="rounded-md border border-warning-100 bg-warning-50 px-3 py-2 text-xs font-medium text-warning-800">
        No brokerage
      </Link>
    )
  }

  if (activeBrokerages.length <= 1 && selectedBrokerage) {
    return (
      <div className="hidden min-w-0 flex-col items-end leading-tight md:flex">
        <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-neutral-500">Brokerage</span>
        <span className="max-w-[220px] truncate text-xs font-semibold text-neutral-800">{selectedBrokerage.name}</span>
      </div>
    )
  }

  return (
    <label className="flex min-w-0 items-center gap-2 text-xs font-medium text-neutral-600">
      <span className="hidden sm:inline">Brokerage</span>
      <select
        value={selectedBrokerageId ?? ''}
        onChange={(event) => selectBrokerage(event.target.value)}
        className="h-9 max-w-[240px] rounded-md border border-neutral-300 bg-white px-2 text-sm font-medium text-neutral-800 outline-none transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
      >
        <option value="" disabled>Select brokerage</option>
        {activeBrokerages.map((brokerage) => (
          <option key={brokerage.brokerage_id} value={brokerage.brokerage_id}>
            {brokerage.name}
          </option>
        ))}
      </select>
    </label>
  )
}

export function BrokerageGate({ children }: { children: React.ReactNode }) {
  const {
    activeBrokerages,
    selectedBrokerageId,
    status,
    errorMessage,
    selectBrokerage,
    refreshBrokerages,
  } = useBrokerageContext()

  if (status === 'loading' || status === 'idle') {
    return (
      <GateShell title="Loading brokerage context" body="Preparing your brokerage workspace." />
    )
  }

  if (status === 'error') {
    return (
      <GateShell
        title="Could not load brokerage context"
        body={errorMessage ?? 'Refresh the membership list and try again.'}
        action={<button type="button" onClick={() => void refreshBrokerages()} className="rounded-md bg-brand-700 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-800">Retry</button>}
      />
    )
  }

  if (status === 'no_membership') {
    return (
      <GateShell
        title="No active brokerage membership"
        body="Ask your brokerage owner or team lead to add you to an active Dalya brokerage workspace."
        action={<Link href="/onboarding/agent" className="rounded-md bg-brand-700 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-800">Open onboarding</Link>}
      />
    )
  }

  if (status === 'selection_required') {
    return (
      <GateShell
        title="Select a brokerage"
        body="Choose the brokerage workspace you want to open. Dalya will not load buyer or listing data until a brokerage is selected."
        action={
          <div className="grid gap-2 sm:grid-cols-2">
            {activeBrokerages.map((brokerage) => (
              <button
                key={brokerage.brokerage_id}
                type="button"
                onClick={() => selectBrokerage(brokerage.brokerage_id)}
                className="rounded-md border border-neutral-200 bg-white p-3 text-left transition-colors hover:border-brand-300 hover:bg-brand-50"
              >
                <span className="block text-sm font-semibold text-neutral-900">{brokerage.name}</span>
                <span className="mt-1 block text-xs text-neutral-500">{brokerage.role}</span>
              </button>
            ))}
          </div>
        }
      />
    )
  }

  return <div key={selectedBrokerageId}>{children}</div>
}

function GateShell({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg rounded-md border border-neutral-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-neutral-900">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-neutral-600">{body}</p>
        {action && <div className="mt-5">{action}</div>}
      </div>
    </div>
  )
}

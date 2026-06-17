'use client'

import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister'

const isBrowser = typeof window !== 'undefined'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            gcTime: 24 * 60 * 60 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  )

  if (!isBrowser) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }

  const persister = createSyncStoragePersister({
    storage: window.localStorage,
    key: 'dalya-query-cache',
  })

  return (
    <PersistQueryClientProvider
      client={client}
      persistOptions={{
        persister,
        maxAge: 60 * 60 * 1000, // 1 hour
      }}
    >
      {children}
    </PersistQueryClientProvider>
  )
}

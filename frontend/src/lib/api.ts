import { createClient } from '@/lib/supabase/client'

export const SELECTED_BROKERAGE_STORAGE_KEY = 'dalya:selected-brokerage-id'
export const BROKERAGE_CONTEXT_REQUIRED_EVENT = 'dalya:brokerage-context-required'
export const BROKERAGE_CONTEXT_FORBIDDEN_EVENT = 'dalya:brokerage-context-forbidden'

const BROKERAGE_SCOPED_API_PREFIXES = [
  '/api/v1/agent',
  '/api/v1/listings',
  '/api/v1/parse-spa',
  '/api/v1/onboarding/me',
]

function isBrowser() {
  return typeof window !== 'undefined'
}

export function getStoredBrokerageId(): string | null {
  if (!isBrowser()) return null
  const stored = window.localStorage.getItem(SELECTED_BROKERAGE_STORAGE_KEY)
  const cleaned = stored?.trim()
  return cleaned || null
}

export function setStoredBrokerageId(brokerageId: string | null) {
  if (!isBrowser()) return
  const cleaned = brokerageId?.trim()
  if (cleaned) {
    window.localStorage.setItem(SELECTED_BROKERAGE_STORAGE_KEY, cleaned)
  } else {
    window.localStorage.removeItem(SELECTED_BROKERAGE_STORAGE_KEY)
  }
}

export function isBrokerageScopedApiPath(path: string): boolean {
  const pathname = path.startsWith('http')
    ? new URL(path).pathname
    : path.split('?')[0]

  return BROKERAGE_SCOPED_API_PREFIXES.some((prefix) => (
    pathname === prefix || pathname.startsWith(`${prefix}/`)
  ))
}

async function handleBrokerageContextResponse(response: Response) {
  if (!isBrowser()) return
  if (response.status !== 403 && response.status !== 409) return

  try {
    const body = await response.clone().json()
    const code = body?.detail?.code
    if (code === 'brokerage_context_required') {
      window.dispatchEvent(new CustomEvent(BROKERAGE_CONTEXT_REQUIRED_EVENT))
    }
    if (code === 'brokerage_context_forbidden') {
      setStoredBrokerageId(null)
      window.dispatchEvent(new CustomEvent(BROKERAGE_CONTEXT_FORBIDDEN_EVENT))
    }
  } catch {
    // Leave the original response untouched; callers keep their normal error handling.
  }
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const supabase = createClient()
  const { data: { session } } = await supabase.auth.getSession()

  const headers = new Headers(init?.headers)
  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`)
  }
  if (session?.access_token && !headers.has('X-Brokerage-Id') && isBrokerageScopedApiPath(path)) {
    const brokerageId = getStoredBrokerageId()
    if (brokerageId) {
      headers.set('X-Brokerage-Id', brokerageId)
    }
  }

  const response = await fetch(path, { ...init, headers })
  await handleBrokerageContextResponse(response)
  return response
}

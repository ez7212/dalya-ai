export function DashboardConnectionErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div id="dashboard" className="marketing-surface min-h-[calc(100vh-4rem)] bg-neutral-50">
      <div className="mx-auto max-w-[1600px]">
        <main className="min-w-0 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <section className="mx-auto mt-10 max-w-2xl rounded-lg border border-error-100 bg-white px-6 py-8 text-center shadow-card-sm">
            <span className="material-symbols-outlined text-[40px] text-error-600" aria-hidden="true">cloud_off</span>
            <p className="mt-4 text-sm font-semibold uppercase tracking-[0.12em] text-error-700">Connection error</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-900">Couldn&apos;t load your live workspace</h1>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-neutral-600">
              Dalya could not reach the dashboard API, so live buyer activity is hidden until the workspace reconnects.
            </p>
            <div className="mx-auto mt-5 max-w-lg rounded-md border border-error-100 bg-error-50 px-4 py-3 text-left">
              <p className="text-sm font-semibold text-error-700">Manual fallback</p>
              <p className="mt-1 text-sm leading-relaxed text-error-700/80">
                Use WhatsApp directly for buyer replies and viewing coordination. Record notes when Dalya reconnects; do not use demo data as live activity.
              </p>
            </div>
            <button
              type="button"
              onClick={onRetry}
              className="mt-6 inline-flex items-center gap-2 rounded-md border border-error-200 bg-white px-3 py-2 text-sm font-medium text-error-700 transition-colors hover:bg-error-50"
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">refresh</span>
              Retry
            </button>
          </section>
        </main>
      </div>
    </div>
  )
}

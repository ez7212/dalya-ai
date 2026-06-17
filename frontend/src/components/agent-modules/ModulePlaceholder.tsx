import Link from 'next/link'

type ModulePlaceholderProps = {
  eyebrow: string
  title: string
  description: string
  primaryHref: string
  primaryLabel: string
  primaryIcon?: string
  items: Array<{
    icon: string
    title: string
    body: string
  }>
}

export function ModulePlaceholder({
  eyebrow,
  title,
  description,
  primaryHref,
  primaryLabel,
  primaryIcon = 'arrow_back',
  items,
}: ModulePlaceholderProps) {
  return (
    <div className="min-h-[calc(100vh-4rem)] bg-neutral-50 text-neutral-700">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
                {eyebrow}
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-neutral-900">{title}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-600">{description}</p>
            </div>
            <Link
              href={primaryHref}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
                {primaryIcon}
              </span>
              {primaryLabel}
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1500px] gap-4 px-4 py-5 sm:px-6 md:grid-cols-3 lg:px-8">
        {items.map((item) => (
          <section key={item.title} className="rounded-lg border border-neutral-200 bg-white p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-brand-50 text-brand-700">
              <span className="material-symbols-outlined text-[21px]" aria-hidden="true">
                {item.icon}
              </span>
            </div>
            <h2 className="mt-4 text-sm font-semibold text-neutral-900">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-600">{item.body}</p>
          </section>
        ))}
      </main>
    </div>
  )
}

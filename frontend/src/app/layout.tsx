import type { Metadata } from 'next'
import { Plus_Jakarta_Sans, JetBrains_Mono, Inter } from 'next/font/google'
import { AuthProvider } from '@/components/providers/AuthProvider'
import { QueryProvider } from '@/components/providers/QueryProvider'
import './globals.css'

// Plus Jakarta Sans + JetBrains Mono retained for the legacy dashboard surface
// (will retire once dashboard is migrated to the B2B brand system).
const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
  variable: '--font-jakarta',
  display: 'swap',
})

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-jetbrains',
  display: 'swap',
})

// Inter — primary font for the B2B brand system. Used by the marketing site
// and the upcoming dashboard rebuild.
const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://dalya.ae'),
  title: 'Dalya · B2B AI infrastructure for Dubai real estate brokerages',
  description:
    'Dalya gives Dubai brokerage agents a sharper working surface for buyer qualification, viewing logistics, follow-up, and serious offer escalation.',
  openGraph: {
    title: 'Dalya · B2B AI infrastructure for Dubai real estate brokerages',
    description: 'AI infrastructure for Dubai brokerages. Built to make every agent sharper.',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,300,0,0&display=swap"
        />
        <style>{`
          .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24;
            vertical-align: middle;
          }
        `}</style>
      </head>
      <body className={`${jakarta.variable} ${jetbrains.variable} ${inter.variable} font-sans`}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-100 focus:px-4 focus:py-2 focus:bg-gold focus:text-ink focus:rounded-md focus:font-semibold"
        >
          Skip to content
        </a>
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  )
}

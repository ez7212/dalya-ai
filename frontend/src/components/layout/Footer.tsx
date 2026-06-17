import Image from 'next/image'
import Link from 'next/link'

const PLATFORM = [
  { label: 'View Listings', href: '/#listings' },
  { label: 'List Your Offplan', href: '/#sell' },
  { label: 'Commission Calculator', href: '#' },
  { label: 'Market Intelligence', href: '/#insights' },
]

const COMPANY = [
  { label: 'About Dalya', href: '/about' },
  { label: 'How It Works', href: '/how-it-works' },
  { label: 'Privacy Policy', href: '#' },
  { label: 'Terms of Service', href: '#' },
]

export function Footer() {
  return (
    <footer className="bg-ink border-t border-gold/10">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 py-16 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="mb-4">
            <Image src="/logo-dalya.png" alt="Dalya AI" height={32} width={538} style={{ width: 'auto', maxHeight: '48px' }} className="object-contain" />
          </div>
          <p className="text-n-500 text-sm font-light leading-relaxed max-w-sm mb-6">
            The premier platform to sell your off-plan.
          </p>
          <div className="text-[11px] text-n-500 space-y-1 mb-6">
            <div>RERA Licensed Broker</div>
            <div>Trakheesi Partner · DLD Registered</div>
          </div>
          <Image src="/logo-mahoroba.png" alt="Mahoroba Realty" height={24} width={941} style={{ width: 'auto', maxHeight: '48px' }} className="object-contain opacity-60" />
        </div>
        <div>
          <div className="text-[11px] text-n-500 uppercase tracking-widest font-semibold mb-4">Platform</div>
          <ul className="space-y-3">
            {PLATFORM.map(l => (
              <li key={l.label}>
                <Link href={l.href} className="text-sm text-n-500 font-light hover:text-sand transition-colors">{l.label}</Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-[11px] text-n-500 uppercase tracking-widest font-semibold mb-4">Company</div>
          <ul className="space-y-3">
            {COMPANY.map(l => (
              <li key={l.label}>
                <Link href={l.href} className="text-sm text-n-500 font-light hover:text-sand transition-colors">{l.label}</Link>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t border-gold/8 max-w-7xl mx-auto px-6 lg:px-10 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="text-[11px] text-n-500">© 2026 Dalya AI. All rights reserved. · <span className="font-medium">دالية</span></div>
        <div className="text-[11px] text-n-500 italic">&ldquo;The most intelligent offplan resale experience.&rdquo;</div>
      </div>
    </footer>
  )
}

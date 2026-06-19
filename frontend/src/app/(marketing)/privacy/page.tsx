import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy — Dalya',
  description:
    'How Dalya handles personal data on this website, and the UAE PDPL basis for it.',
}

const SECTIONS = [
  {
    h: 'What we collect',
    p: 'When you book a demo, we collect the details you submit: your name, work email, brokerage name, and any message you add. We do not run advertising trackers or sell data collected on this site.',
  },
  {
    h: 'How we use it',
    p: 'We use those details only to respond to your enquiry and arrange a demo. The demo request is delivered to our team by email; we do not share it with third parties for their own marketing.',
  },
  {
    h: 'Lawful basis (UAE PDPL)',
    p: 'We process this information on the basis of your consent — you provide it when you choose to contact us. You can withdraw that consent at any time by emailing us.',
  },
  {
    h: 'Buyer data inside the product',
    p: 'Personal data processed inside the Dalya product on behalf of a brokerage (buyer conversations, contacts, offers) is separate from this website. It is isolated per brokerage, kept under audit, and governed by the agreement with that brokerage rather than this notice.',
  },
  {
    h: 'Your rights',
    p: 'You can ask us to access, correct, or delete the personal data you have shared with us. Email eric@dalya.ae and we will action it.',
  },
]

export default function PrivacyPage() {
  return (
    <section className="max-w-[760px] mx-auto px-6 lg:px-8 pt-20 pb-24 lg:pt-28">
      <div className="t-eyebrow mb-4">Privacy</div>
      <h1 className="t-display mb-5">Your data, handled plainly.</h1>
      <p className="t-large mb-12">
        This notice covers personal data collected on this website. Dalya is a Dubai-based
        B2B platform; every listing on the platform is operated by a RERA-licensed brokerage.
      </p>

      <div className="flex flex-col gap-10">
        {SECTIONS.map((s) => (
          <div key={s.h}>
            <h2
              className="text-lg font-semibold mb-2"
              style={{ color: 'var(--color-text-1)', letterSpacing: '-0.01em' }}
            >
              {s.h}
            </h2>
            <p className="text-[15px] leading-relaxed" style={{ color: 'var(--color-text-2)' }}>
              {s.p}
            </p>
          </div>
        ))}
      </div>

      <p className="text-[13px] mt-12" style={{ color: 'var(--color-text-3)' }}>
        Questions about your data? Email{' '}
        <a href="mailto:eric@dalya.ae" style={{ color: 'var(--color-brand-500)' }}>eric@dalya.ae</a>.
      </p>
    </section>
  )
}

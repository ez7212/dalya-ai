import { NextResponse } from 'next/server'
import { Resend } from 'resend'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// Where demo requests land, and the verified sender they come from.
const TO_EMAIL = process.env.CONTACT_TO_EMAIL || 'eric@dalya.ae'
const FROM_EMAIL = process.env.CONTACT_FROM_EMAIL || 'Dalya Website <notifications@dalya.ae>'

const MAX = { name: 200, email: 320, brokerage: 200, notes: 5000 }

function clean(v: unknown, max: number): string {
  return typeof v === 'string' ? v.trim().slice(0, max) : ''
}

// Strip CR/LF so user input can never inject mail headers via the subject.
function oneLine(v: string): string {
  return v.replace(/[\r\n]+/g, ' ')
}

function isEmail(v: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
}

export async function POST(req: Request) {
  let payload: Record<string, unknown>
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 })
  }

  // Honeypot — real users never fill this hidden field; bots do.
  if (clean(payload.company, 100)) {
    return NextResponse.json({ ok: true })
  }

  const name = clean(payload.name, MAX.name)
  const email = clean(payload.email, MAX.email)
  const brokerage = clean(payload.brokerage, MAX.brokerage)
  const notes = clean(payload.notes, MAX.notes)

  if (!name || !brokerage || !isEmail(email)) {
    return NextResponse.json(
      { error: 'Please add your name, a valid work email, and your brokerage.' },
      { status: 422 },
    )
  }

  const apiKey = process.env.RESEND_API_KEY
  if (!apiKey) {
    console.error('[contact] RESEND_API_KEY is not set — cannot send demo request email.')
    return NextResponse.json({ error: 'Email is not configured yet.' }, { status: 503 })
  }

  const text = [
    `New demo request from the Dalya website`,
    ``,
    `Brokerage: ${brokerage}`,
    `Name: ${name}`,
    `Email: ${email}`,
    notes ? `\nNotes:\n${notes}` : null,
  ]
    .filter((l) => l !== null)
    .join('\n')

  try {
    const resend = new Resend(apiKey)
    const { error } = await resend.emails.send({
      from: FROM_EMAIL,
      to: [TO_EMAIL],
      replyTo: email,
      subject: oneLine(`Dalya demo request: ${brokerage}`),
      text,
    })
    if (error) {
      console.error('[contact] Resend error:', error)
      return NextResponse.json({ error: 'Could not send right now.' }, { status: 502 })
    }
    return NextResponse.json({ ok: true })
  } catch (err) {
    console.error('[contact] send failed:', err)
    return NextResponse.json({ error: 'Could not send right now.' }, { status: 502 })
  }
}

import { ImageResponse } from 'next/og'

export const alt = 'Dalya — AI infrastructure for Dubai brokerages'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

// Branded share card. On-brand: warm-neutral surface, slate wordmark,
// ink tagline. Default font (no external fetch) keeps it fast + reliable.
export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          background: '#FAFAF9',
          padding: '88px',
        }}
      >
        <div
          style={{
            fontSize: 104,
            fontWeight: 700,
            color: '#3D5A80',
            letterSpacing: '-0.04em',
          }}
        >
          dalya
        </div>
        <div
          style={{
            fontSize: 46,
            fontWeight: 600,
            color: '#3D3D39',
            letterSpacing: '-0.02em',
            lineHeight: 1.15,
            marginTop: 28,
            maxWidth: 940,
          }}
        >
          The intelligent operating layer for Dubai brokerages.
        </div>
        <div
          style={{
            fontSize: 27,
            color: '#5C5C57',
            marginTop: 36,
          }}
        >
          24/7 buyer concierge · smart escalation · morning hot list · viewing logistics
        </div>
      </div>
    ),
    { ...size },
  )
}

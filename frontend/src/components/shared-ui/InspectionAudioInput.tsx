'use client'

import { useEffect, useRef, useState } from 'react'
import { sharedUi } from '@/lib/shared-ui-tokens'

export type InspectionAudioSource = 'recording' | 'upload'

export interface InspectionAudioReady {
  file: File
  source: InspectionAudioSource
  durationSeconds: number | null
  contentType: string
}

interface InspectionAudioInputProps {
  maxLengthSeconds?: number
  disabled?: boolean
  onAudioReady: (audio: InspectionAudioReady) => void | Promise<void>
  onDiscard?: () => void
}

const ACCEPTED_AUDIO = 'audio/m4a,audio/x-m4a,audio/mp4,audio/mpeg,audio/mp3,audio/ogg,audio/opus,audio/wav,audio/webm,.m4a,.mp3,.opus,.ogg,.wav,.webm'

export function InspectionAudioInput({
  maxLengthSeconds = 900,
  disabled = false,
  onAudioReady,
  onDiscard,
}: InspectionAudioInputProps) {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const startedAtRef = useRef<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [recording, setRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [level, setLevel] = useState(0)
  const [pending, setPending] = useState<InspectionAudioReady | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const cleanupStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  useEffect(() => {
    if (!recording) return
    const interval = window.setInterval(() => {
      const started = startedAtRef.current || Date.now()
      const nextElapsed = Math.floor((Date.now() - started) / 1000)
      setElapsed(nextElapsed)
      setLevel((current) => (current + 23) % 100)
      if (nextElapsed >= maxLengthSeconds) {
        stopRecording()
      }
    }, 250)
    return () => window.clearInterval(interval)
  }, [recording, maxLengthSeconds])

  useEffect(() => () => cleanupStream(), [])

  const startRecording = async () => {
    setError(null)
    setPending(null)
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
        setError('Audio recording is not available in this browser. Upload an audio memo instead.')
        return
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream)
      recorderRef.current = recorder
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data)
      }
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: mimeType })
        const file = new File([blob], `inspection-note-${Date.now()}.${extensionFor(mimeType)}`, { type: mimeType })
        setPending({
          file,
          source: 'recording',
          durationSeconds: elapsed || null,
          contentType: mimeType,
        })
        cleanupStream()
      }
      startedAtRef.current = Date.now()
      setElapsed(0)
      recorder.start()
      setRecording(true)
    } catch {
      cleanupStream()
      setError('Microphone access was blocked. Allow microphone access or upload an existing audio memo.')
    }
  }

  const stopRecording = () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    setRecording(false)
  }

  const discard = () => {
    setPending(null)
    chunksRef.current = []
    onDiscard?.()
  }

  const confirm = async () => {
    if (!pending) return
    await onAudioReady(pending)
    setPending(null)
  }

  const handleFile = (file: File | null) => {
    if (!file) return
    setError(null)
    if (!isSupportedAudio(file)) {
      setError('Upload an audio file in m4a, mp3, opus, ogg, wav, or webm format.')
      return
    }
    setPending({
      file,
      source: 'upload',
      durationSeconds: null,
      contentType: file.type || contentTypeForName(file.name),
    })
  }

  return (
    <div className={`${sharedUi.panel} p-4 sm:p-5`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={sharedUi.label}>Inspection audio</p>
          <h3 className={`${sharedUi.heading} mt-1`}>Record or upload notes</h3>
          <p className={`${sharedUi.muted} mt-1 max-w-xl`}>
            Audio is used only for this listing&apos;s inspection profile. The component captures audio and hands it off for transcription.
          </p>
        </div>
        <span className={`${sharedUi.mono} text-text-3`}>Max {formatTimer(maxLengthSeconds)}</span>
      </div>

      {error && (
        <p className="mt-4 rounded border border-error-100 bg-error-50 px-3 py-2 text-sm text-error-700" role="alert">
          {error}
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr]">
        <div className={sharedUi.inset + ' p-4'}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-text-1">{recording ? 'Recording now' : 'Live recording'}</p>
              <p className={`${sharedUi.muted} mt-0.5`}>{formatTimer(elapsed)}</p>
            </div>
            <div className="flex items-center gap-1" aria-label="Input level">
              {[20, 40, 60, 80].map((threshold) => (
                <span
                  key={threshold}
                  className={`block w-1.5 rounded bg-brand-500 transition-all ${level >= threshold || recording ? 'opacity-100' : 'opacity-25'}`}
                  style={{ height: recording ? `${12 + threshold / 2}px` : '14px' }}
                />
              ))}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {!recording ? (
              <button type="button" onClick={startRecording} disabled={disabled} className={sharedUi.primaryButton}>
                <span className="material-symbols-rounded text-[18px]" aria-hidden="true">mic</span>
                Record
              </button>
            ) : (
              <button type="button" onClick={stopRecording} className={sharedUi.secondaryButton}>
                <span className="material-symbols-rounded text-[18px]" aria-hidden="true">stop</span>
                Stop
              </button>
            )}
            <button type="button" onClick={discard} disabled={disabled || recording || !pending} className={sharedUi.secondaryButton}>
              Discard
            </button>
          </div>
        </div>

        <div
          className={`${sharedUi.inset} p-4 ${dragActive ? 'border-brand-500 bg-brand-50' : ''}`}
          onDragOver={(event) => {
            event.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragActive(false)
            handleFile(event.dataTransfer.files?.[0] || null)
          }}
        >
          <p className="text-sm font-medium text-text-1">Upload a memo</p>
          <p className={`${sharedUi.muted} mt-0.5`}>Voice Memos exports and WhatsApp audio files are supported.</p>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_AUDIO}
            className="hidden"
            onChange={(event) => handleFile(event.target.files?.[0] || null)}
          />
          <button type="button" onClick={() => fileInputRef.current?.click()} disabled={disabled || recording} className={`${sharedUi.secondaryButton} mt-4`}>
            <span className="material-symbols-rounded text-[18px]" aria-hidden="true">upload_file</span>
            Choose audio
          </button>
        </div>
      </div>

      {pending && (
        <div className="mt-4 rounded border border-brand-100 bg-brand-50 p-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-brand-900">{pending.file.name}</p>
              <p className={sharedUi.muted}>
                {pending.source === 'recording' ? 'Recorded audio' : 'Uploaded memo'} · {(pending.file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={discard} className={sharedUi.secondaryButton}>Re-record</button>
              <button type="button" onClick={confirm} className={sharedUi.primaryButton}>Process notes</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function isSupportedAudio(file: File): boolean {
  const name = file.name.toLowerCase()
  return Boolean(
    file.type.startsWith('audio/') ||
    ['.m4a', '.mp3', '.opus', '.ogg', '.wav', '.webm'].some((ext) => name.endsWith(ext))
  )
}

function contentTypeForName(name: string): string {
  const lower = name.toLowerCase()
  if (lower.endsWith('.m4a')) return 'audio/x-m4a'
  if (lower.endsWith('.mp3')) return 'audio/mpeg'
  if (lower.endsWith('.opus')) return 'audio/opus'
  if (lower.endsWith('.ogg')) return 'audio/ogg'
  if (lower.endsWith('.wav')) return 'audio/wav'
  return 'audio/webm'
}

function extensionFor(mimeType: string): string {
  if (mimeType.includes('ogg')) return 'ogg'
  if (mimeType.includes('mpeg')) return 'mp3'
  if (mimeType.includes('mp4')) return 'm4a'
  if (mimeType.includes('wav')) return 'wav'
  return 'webm'
}

function formatTimer(seconds: number): string {
  const mins = Math.floor(seconds / 60).toString().padStart(2, '0')
  const secs = Math.floor(seconds % 60).toString().padStart(2, '0')
  return `${mins}:${secs}`
}

'use client'

import { use, useRef, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { useAuth } from '@/components/providers/AuthProvider'
import { useAdminConversationMessages } from '@/lib/queries'

export default function ConversationTranscriptPage({
  params,
}: {
  params: Promise<{ phone: string; id: string }>
}) {
  const { phone: rawPhone, id: conversationId } = use(params)
  const phone = decodeURIComponent(rawPhone)

  const { loading: authLoading } = useAuth()
  const { data, isLoading, error } = useAdminConversationMessages(
    phone,
    conversationId,
    !authLoading,
  )

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (data?.messages && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [data?.messages])

  if (isLoading || authLoading) {
    return <p className="text-n-500 text-sm py-10 text-center">Loading conversation...</p>
  }
  if (error) {
    return <p className="text-red-400 text-sm py-10 text-center" role="alert">{error.message}</p>
  }
  if (!data) return null

  const encodedPhone = encodeURIComponent(phone)
  const messages = data.messages ?? []

  const dateRange =
    messages.length > 0
      ? `${new Date(messages[0].timestamp).toLocaleDateString()} — ${new Date(messages[messages.length - 1].timestamp).toLocaleDateString()}`
      : ''

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Back link */}
      <Link
        href={`/admin/crm/${encodedPhone}`}
        className="inline-flex items-center gap-1.5 text-sm text-n-500 hover:text-gold transition-colors mb-6"
      >
        <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
          arrow_back
        </span>
        Back to {data.buyer_name || 'buyer'}
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="editorial text-xl md:text-2xl font-bold text-sand tracking-tight">
          {data.listing_name}
        </h1>
        {dateRange && (
          <p className="text-xs text-n-500 mt-1">{dateRange}</p>
        )}
      </div>

      {/* Chat transcript */}
      <div className="surface-1 rounded-xl ghost-border overflow-hidden">
        <div
          ref={scrollRef}
          className="p-6 space-y-4 max-h-[70vh] overflow-y-auto"
        >
          {messages.length === 0 ? (
            <p className="text-n-500 text-sm text-center py-10">No messages.</p>
          ) : (
            messages.map((msg, i) => {
              const isBuyer = msg.role === 'user'
              return (
                <div
                  key={msg.id || i}
                  className={`flex ${isBuyer ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] rounded-xl px-4 py-3 ${
                      msg.escalated
                        ? 'border-l-2 border-gold'
                        : ''
                    } ${
                      isBuyer
                        ? 'bg-sage/20 text-sand rounded-br-sm'
                        : 'bg-slate/60 text-sand rounded-bl-sm'
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-[10px] text-n-500">
                        {new Date(msg.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      {msg.intent && (
                        <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-gold/10 text-gold">
                          {msg.intent}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </motion.div>
  )
}

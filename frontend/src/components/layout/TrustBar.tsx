export function TrustBar() {
  return (
    <div className="fixed top-16 w-full z-40 bg-ink/70 backdrop-blur-sm border-b border-gold/10">
      <div className="max-w-7xl mx-auto px-6 lg:px-10 h-9 flex items-center justify-center gap-6 md:gap-10">
        <span className="text-[11px] text-n-300 tracking-wide">RERA Licensed Broker</span>
        <span className="text-gold/30">|</span>
        <span className="text-[11px] text-n-300 tracking-wide">Trakheesi Partner</span>
        <span className="text-gold/30">|</span>
        <span className="text-[11px] text-n-300 tracking-wide">DLD Registered</span>
        <span className="text-gold/30 hidden md:block">|</span>
        <span className="hidden md:block text-[11px] text-n-300 tracking-wide">Every listing sourced from the actual SPA</span>
      </div>
    </div>
  )
}

# Waraqah Frontend Spec — "Lattice" design implementation
Source of truth: "C:/Users/Hamad/Downloads/Stock Analyzer UI Design/design-spec.md"
(read it fully) + reference mockup Stock Analyzer.dc.html + uploads/pasted-*.png.

Build a Next.js (App Router, TypeScript, Tailwind) frontend in ./frontend that:
- Implements the Lattice visual system exactly (tokens in spec: canvas #e9e7e2,
  white cards radius 20, ink hierarchy, up #12a55f / down #e5484d, agent accent
  #5b46d8 on #f1eeff, Manrope UI + JetBrains Mono numerals, 12px gutters).
- Three-column layout: chart workspace (fluid) | AI Analyst right rail 372px
  | icon rail 52px. Header: brand "ورقة Waraqah", omni-search (⌘K), portfolio chip.
- Chart: candlesticks + SMA10 + volume histogram (use lightweight-charts npm pkg,
  TradingView's free lib). Ticker tabs bottom. Agent annotations layer (purple,
  dashed) — render from API insight data when present.
- AI Analyst panel: live-status pulse, insight cards (headline, 2-line thesis,
  bull/bear evidence bullets, confidence badge, "Show on chart" + "Sources"),
  conversation with metric tiles, provenance line, suggested prompt chips,
  composer with scope chip. All agent-authored pixels purple/dashed-purple.
- Watchlist under analyst: agent-ranked with signal pills (Breakout/Overbought/
  Accumulating/Weak tape), Arabic labels alongside English.
- Data source: Waraqah backend at NEXT_PUBLIC_API_URL (default http://localhost:8123).
  Wire: /stock/{symbol} (profile+metrics+returns), /screener, /compare, /movers,
  /macro, /alerts, /portfolio POST, /agent/chat POST (render 501 gracefully as
  "Agent coming online" state). Use SWR or react-query for polling.
- The AI chat panel calls /agent/chat; until backend returns real answers, the UI
  shows the offline state — no fake responses.
- RTL-ready: Arabic-first labels with English secondary (dir=rtl on root is fine).
- Placeholder friendly: when DB empty, show Arabic empty-states (spec section 5).
- npm run build must pass. Commit + push to Hxhamad/Waraqah main.

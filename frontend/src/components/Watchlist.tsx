'use client';

import { useMovers } from '@/lib/api';

interface WatchlistProps {
  onSelectSymbol: (symbol: string) => void;
  selectedSymbol: string | null;
}

const SIGNAL_LABELS: Record<string, { en: string; ar: string; style: string }> = {
  high: { en: 'Breakout', ar: 'اختراق', style: 'bg-[#fdf1e7] text-[#c2410c]' },
  moderate: { en: 'Accumulating', ar: 'تجميع', style: 'bg-[#e6f6ee] text-[#0f8f52]' },
  low: { en: 'Weak tape', ar: 'ضعيف', style: 'bg-[#f4f3f0] text-[#6c6b67]' },
};

function getSignal(changePct: number): { en: string; ar: string; style: string } {
  if (changePct > 1) return { en: 'Breakout', ar: 'اختراق', style: 'bg-[#fdf1e7] text-[#c2410c]' };
  if (changePct > 0) return { en: 'Accumulating', ar: 'تجميع', style: 'bg-[#e6f6ee] text-[#0f8f52]' };
  if (changePct > -1) return { en: 'Flat', ar: 'مستقر', style: 'bg-[#f1eeff] text-[#5b46d8]' };
  if (changePct > -2) return { en: 'Weak tape', ar: 'ضعيف', style: 'bg-[#f4f3f0] text-[#6c6b67]' };
  return { en: 'Overbought', ar: 'ذروة بيع', style: 'bg-[#fee2e2] text-[#e5484d]' };
}

export default function Watchlist({ onSelectSymbol, selectedSymbol }: WatchlistProps) {
  const { data: movers, isLoading, error } = useMovers(10);

  const stocks = movers ? [...movers.gainers, ...movers.losers.slice(0, 2)] : [];

  if (isLoading) {
    return (
      <div className="bg-white rounded-[20px] shadow-[0_1px_2px_rgba(20,20,25,0.06)] p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[13.5px] font-extrabold">Watchlist</span>
          <span className="font-mono text-[9.5px] font-semibold text-[#8b8a86] bg-[#f4f3f0] rounded-md px-1.5 py-0.5">loading...</span>
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 bg-[#f4f3f0] rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || stocks.length === 0) {
    return (
      <div className="bg-white rounded-[20px] shadow-[0_1px_2px_rgba(20,20,25,0.06)] p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[13.5px] font-extrabold">Watchlist</span>
          <span className="font-mono text-[9.5px] font-semibold text-[#8b8a86] bg-[#f4f3f0] rounded-md px-1.5 py-0.5">agent-ranked</span>
        </div>
        <div className="text-center py-6 text-[#8b8a86]">
          <div className="text-[13px] font-semibold">No stocks yet</div>
          <div className="text-[11px] mt-1">Add stocks to your watchlist</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-[20px] shadow-[0_1px_2px_rgba(20,20,25,0.06)] p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[13.5px] font-extrabold">Watchlist</span>
        <span className="font-mono text-[9.5px] font-semibold text-[#8b8a86] bg-[#f4f3f0] rounded-md px-1.5 py-0.5">agent-ranked</span>
        <span className="ms-auto text-base text-[#a3a29d] font-medium cursor-pointer">+</span>
      </div>

      <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1 text-[9.5px] font-bold text-[#a3a29d] tracking-wide mb-2">
        <div>SYMBOL</div>
        <div className="text-end">LAST</div>
        <div className="text-end w-20">SIGNAL</div>
      </div>

      <div className="space-y-1.5">
        {stocks.slice(0, 7).map((stock) => {
          const signal = getSignal(stock.change_pct);
          const isSelected = selectedSymbol === stock.symbol;

          return (
            <button
              key={stock.symbol}
              onClick={() => onSelectSymbol(stock.symbol)}
              className={`w-full grid grid-cols-[1fr_auto_auto] gap-3 items-center py-1 rounded-lg transition-colors ${
                isSelected ? 'bg-[#f1eeff]' : 'hover:bg-[#f4f3f0]'
              }`}
            >
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-[#f4f3f0] flex items-center justify-center font-mono text-[8px] font-bold text-[#6c6b67]">
                  {stock.symbol.slice(0, 2)}
                </div>
                <span className="text-[12px] font-bold">{stock.symbol}</span>
                <span className="text-[10.5px] text-[#a3a29d] font-semibold truncate max-w-[80px]">{stock.name?.split(' ')[0]}</span>
              </div>
              <div className="text-end font-mono text-[12px] font-semibold">{stock.price.toFixed(2)}</div>
              <div className={`text-center w-20 font-mono text-[9.5px] font-semibold rounded-md py-0.5 ${signal.style}`}>
                {signal.en}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

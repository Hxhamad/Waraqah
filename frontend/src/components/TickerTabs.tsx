'use client';

interface TickerTabsProps {
  tabs: Array<{ symbol: string; name: string }>;
  activeSymbol: string | null;
  onSelect: (symbol: string) => void;
  onAdd: () => void;
}

export default function TickerTabs({ tabs, activeSymbol, onSelect, onAdd }: TickerTabsProps) {
  return (
    <div className="bg-white rounded-2xl shadow-[0_1px_2px_rgba(20,20,25,0.06)] px-2.5 py-1.5 flex items-center gap-2">
      <button
        onClick={onAdd}
        className="w-7 h-7 rounded-lg bg-[#f4f3f0] flex items-center justify-center text-[15px] text-[#8b8a86] font-medium hover:bg-[#eceae6]"
      >
        +
      </button>
      {tabs.map((tab) => {
        const isActive = tab.symbol === activeSymbol;
        return (
          <button
            key={tab.symbol}
            onClick={() => onSelect(tab.symbol)}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-[11.5px] font-semibold transition-colors ${
              isActive ? 'bg-[#f4f3f0] font-bold text-[#15161a]' : 'text-[#6c6b67] hover:bg-[#f9f9f8]'
            }`}
          >
            <div className={`w-3.5 h-3.5 rounded ${isActive ? 'bg-[#15161a]' : 'bg-[#d9d7d1]'}`} />
            {tab.name}
          </button>
        );
      })}
    </div>
  );
}

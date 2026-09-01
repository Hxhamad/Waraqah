'use client';

import { useState } from 'react';

interface HeaderProps {
  onSearch: (query: string) => void;
  portfolioValue?: number;
  portfolioChange?: number;
  buyingPower?: number;
}

export default function Header({ onSearch, portfolioValue = 248913.40, portfolioChange = 2.14, buyingPower = 31204.88 }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim());
      setSearchQuery('');
    }
  };

  return (
    <div className="flex items-center gap-5 bg-white rounded-[20px] px-4 py-3 shadow-[0_1px_2px_rgba(20,20,25,0.06)]">
      <div className="flex items-center gap-3 pe-5 border-e border-[#eceae6]">
        <div className="w-[38px] h-[38px] rounded-full bg-[#15161a] flex items-center justify-center">
          <div className="w-[13px] h-[13px] rounded-[3px] bg-white rotate-45" />
        </div>
        <div className="flex flex-col gap-0.5">
          <div className="text-base font-extrabold tracking-tight">Waraqah</div>
          <div className="text-[10.5px] text-[#8b8a86] font-medium">agentic market research</div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 flex-1 bg-[#f4f3f0] rounded-xl px-3.5 py-2 max-w-[520px]">
        <div className="w-[13px] h-[13px] border-[1.5px] border-[#a3a29d] rounded-full" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder='Ask anything — "compare VLTA margins to sector"'
          className="flex-1 bg-transparent text-[12.5px] text-[#15161a] placeholder:text-[#8b8a86] font-medium outline-none"
        />
        <div className="ms-auto font-mono text-[10px] font-semibold text-[#a3a29d] bg-white rounded-md px-1.5 py-0.5">K</div>
      </form>

      <div className="flex items-center gap-5 ms-auto">
        <div className="flex flex-col gap-0.5 items-end">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold">${portfolioValue.toLocaleString()}</span>
            <span className={`font-mono text-[10.5px] font-semibold rounded-md px-1.5 py-0.5 ${portfolioChange >= 0 ? 'bg-[#e2f6ea] text-[#0f8f52]' : 'bg-red-100 text-[#e5484d]'}`}>
              {portfolioChange >= 0 ? '+' : ''}{portfolioChange.toFixed(2)}%
            </span>
          </div>
          <div className="text-[10.5px] text-[#8b8a86] font-medium">Portfolio USD</div>
        </div>

        <div className="flex flex-col gap-0.5 items-end">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold">${buyingPower.toLocaleString()}</span>
            <span className="font-mono text-[10.5px] font-semibold bg-[#f4f3f0] text-[#6c6b67] rounded-md px-1.5 py-0.5">cash</span>
          </div>
          <div className="text-[10.5px] text-[#8b8a86] font-medium">Buying power</div>
        </div>

        <div className="flex items-center gap-2 bg-[#15161a] rounded-full py-1.5 ps-3.5 pe-1.5">
          <span className="text-[11px] font-bold text-white tracking-wide">PRO</span>
          <div className="w-[30px] h-[30px] rounded-full bg-gradient-to-br from-[#c9c6bf] to-[#8f8c85]" />
        </div>
      </div>
    </div>
  );
}

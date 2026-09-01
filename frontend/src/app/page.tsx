'use client';

import { useState, useCallback } from 'react';
import { SWRConfig } from 'swr';
import Header from '@/components/Header';
import Chart from '@/components/Chart';
import AnalystPanel from '@/components/AnalystPanel';
import Watchlist from '@/components/Watchlist';
import IconRail from '@/components/IconRail';
import TickerTabs from '@/components/TickerTabs';
import { useStock } from '@/lib/api';

function AppContent() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('7010');
  const [openTabs, setOpenTabs] = useState<Array<{ symbol: string; name: string }>>([
    { symbol: '7010', name: 'Saudi Telecom' },
  ]);

  const { data: stock, isLoading } = useStock(selectedSymbol);

  const handleSearch = useCallback((query: string) => {
    const symbolMatch = query.match(/^\d{4}$/);
    if (symbolMatch) {
      setSelectedSymbol(query);
      if (!openTabs.find((t) => t.symbol === query)) {
        setOpenTabs((prev) => [...prev, { symbol: query, name: query }]);
      }
    }
  }, [openTabs]);

  const handleSelectSymbol = useCallback((symbol: string) => {
    setSelectedSymbol(symbol);
    if (!openTabs.find((t) => t.symbol === symbol)) {
      setOpenTabs((prev) => [...prev, { symbol, name: symbol }]);
    }
  }, [openTabs]);

  const handleAddTab = useCallback(() => {
    const prompt = window.prompt('Enter stock symbol (e.g., 7010, 2222):');
    if (prompt && /^\d{4}$/.test(prompt)) {
      handleSelectSymbol(prompt);
    }
  }, [handleSelectSymbol]);

  return (
    <div className="w-full max-w-[1440px] mx-auto p-5 flex flex-col gap-3">
      <Header onSearch={handleSearch} />

      <div className="flex gap-3 h-[812px]">
        <div className="flex-1 min-w-0 flex flex-col gap-2.5">
          <Chart stock={stock ?? null} loading={isLoading} />
          <TickerTabs
            tabs={openTabs}
            activeSymbol={selectedSymbol}
            onSelect={setSelectedSymbol}
            onAdd={handleAddTab}
          />
        </div>

        <div className="w-[372px] flex flex-col gap-3">
          <AnalystPanel stock={stock ?? null} />
          <Watchlist onSelectSymbol={handleSelectSymbol} selectedSymbol={selectedSymbol} />
        </div>

        <IconRail />
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <SWRConfig
      value={{
        revalidateOnFocus: false,
        shouldRetryOnError: false,
      }}
    >
      <AppContent />
    </SWRConfig>
  );
}

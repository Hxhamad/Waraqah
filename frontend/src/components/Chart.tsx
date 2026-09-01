'use client';

import { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, CandlestickData, HistogramData, LineData, Time } from 'lightweight-charts';
import type { StockProfile } from '@/lib/types';

interface ChartProps {
  stock: StockProfile | null;
  loading?: boolean;
}

function generateMockCandles(basePrice: number, count: number): { candles: CandlestickData<Time>[]; volumes: HistogramData<Time>[]; sma: LineData<Time>[] } {
  const candles: CandlestickData<Time>[] = [];
  const volumes: HistogramData<Time>[] = [];
  const closes: number[] = [];

  let price = basePrice * 0.9;
  const now = new Date();

  for (let i = count; i > 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const time = Math.floor(date.getTime() / 1000) as Time;

    const drift = i > count * 0.6 ? -0.15 : 1.2;
    const open = price;
    const close = Math.max(basePrice * 0.85, open + drift + (Math.random() - 0.48) * basePrice * 0.015);
    const high = Math.max(open, close) + Math.random() * basePrice * 0.008;
    const low = Math.min(open, close) - Math.random() * basePrice * 0.008;

    price = close;
    closes.push(close);

    candles.push({ time, open, high, low, close });
    volumes.push({
      time,
      value: (0.3 + Math.random() * 0.7) * 10000000,
      color: close >= open ? 'rgba(18,165,95,0.28)' : 'rgba(229,72,77,0.28)',
    });
  }

  const sma: LineData<Time>[] = candles.map((c, i) => {
    const window = closes.slice(Math.max(0, i - 9), i + 1);
    const avg = window.reduce((a, b) => a + b, 0) / window.length;
    return { time: c.time, value: avg };
  });

  return { candles, volumes, sma };
}

export default function Chart({ stock }: ChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const candleSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const smaSeriesRef = useRef<any>(null);
  /* eslint-enable @typescript-eslint/no-explicit-any */
  const [agentOverlay, setAgentOverlay] = useState(true);
  const [lastCandle, setLastCandle] = useState<CandlestickData<Time> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#ffffff' },
        textColor: '#6c6b67',
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        vertLines: { color: '#f6f5f2' },
        horzLines: { color: '#f6f5f2' },
      },
      crosshair: {
        vertLine: { color: '#c9c6bf', style: 1 },
        horzLine: { color: '#c9c6bf', style: 1 },
      },
      rightPriceScale: {
        borderColor: '#f6f5f2',
      },
      timeScale: {
        borderColor: '#f6f5f2',
        timeVisible: true,
      },
    });

    // Use type assertion to bypass strict typing in v5
    const candleSeries = (chart as any).addCandlestickSeries({
      upColor: '#12a55f',
      downColor: '#e5484d',
      borderUpColor: '#12a55f',
      borderDownColor: '#e5484d',
      wickUpColor: '#12a55f',
      wickDownColor: '#e5484d',
    });

    const volumeSeries = (chart as any).addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });

    const smaSeries = (chart as any).addLineSeries({
      color: '#9a9791',
      lineWidth: 2,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    smaSeriesRef.current = smaSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !smaSeriesRef.current) return;

    const basePrice = stock?.price || 100;
    const { candles, volumes, sma } = generateMockCandles(basePrice, 60);

    candleSeriesRef.current.setData(candles);
    volumeSeriesRef.current.setData(volumes);
    smaSeriesRef.current.setData(sma);

    if (candles.length > 0) {
      setLastCandle(candles[candles.length - 1]);
    }

    chartRef.current?.timeScale().fitContent();
  }, [stock?.code, stock?.price]);

  const displayPrice = stock?.price || lastCandle?.close || 0;
  const displayOpen = lastCandle?.open || displayPrice;
  const displayHigh = lastCandle?.high || displayPrice;
  const displayLow = lastCandle?.low || displayPrice;
  const displayClose = lastCandle?.close || displayPrice;
  const priceUp = displayClose >= displayOpen;

  return (
    <div className="flex-1 min-h-0 bg-white rounded-[20px] shadow-[0_1px_2px_rgba(20,20,25,0.06)] flex flex-col p-3">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-[#f4f3f0] rounded-full py-1.5 ps-1.5 pe-3.5">
          <div className="w-6 h-6 rounded-full bg-[#15161a] text-white flex items-center justify-center font-mono text-[10px] font-bold">
            {stock?.code?.slice(0, 2) || 'VL'}
          </div>
          <span className="text-[13px] font-bold">{stock?.name || 'Loading...'}</span>
          <span className="text-[11.5px] text-[#8b8a86] font-semibold">{stock?.sector?.split(' ')[0] || 'Tadawul'}</span>
          <span className={`font-mono text-[10.5px] font-semibold ${priceUp ? 'text-[#0f8f52]' : 'text-[#e5484d]'}`}>
            {stock?.returns?.['1W'] !== undefined ? `${(stock.returns['1W'] * 100).toFixed(2)}%` : '+0.00%'}
          </span>
        </div>

        <div className="flex gap-2">
          <div className="bg-[#f4f3f0] rounded-xl px-4 py-2 flex flex-col items-center gap-0.5">
            <span className="text-[9.5px] font-bold text-[#8b8a86] tracking-wide">SELL</span>
            <span className="font-mono text-[13px] font-semibold">{(displayPrice * 0.9995).toFixed(2)}</span>
          </div>
          <div className="bg-[#0f8f52] rounded-xl px-4 py-2 flex flex-col items-center gap-0.5">
            <span className="text-[9.5px] font-bold text-white/75 tracking-wide">BUY</span>
            <span className="font-mono text-[13px] font-semibold text-white">{displayPrice.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex gap-3.5 font-mono text-[11.5px] font-medium text-[#6c6b67]">
          <span>O <b className="text-[#15161a] font-semibold">{displayOpen.toFixed(2)}</b></span>
          <span>H <b className="text-[#15161a] font-semibold">{displayHigh.toFixed(2)}</b></span>
          <span>L <b className="text-[#15161a] font-semibold">{displayLow.toFixed(2)}</b></span>
          <span>C <b className={`font-semibold ${priceUp ? 'text-[#0f8f52]' : 'text-[#e5484d]'}`}>{displayClose.toFixed(2)}</b></span>
        </div>

        <div className="ms-auto flex gap-1.5">
          <div className="w-7 h-7 rounded-lg bg-[#f4f3f0] flex items-center justify-center">
            <div className="w-[11px] h-[11px] border-[1.5px] border-[#8b8a86] rounded-[3px]" />
          </div>
          <div className="w-7 h-7 rounded-lg bg-[#f4f3f0] flex items-center justify-center">
            <div className="w-[11px] h-[11px] border-[1.5px] border-[#8b8a86]" />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3">
        <div className="flex items-center gap-2 border border-[#eceae6] rounded-full px-3 py-1.5 text-[11.5px] font-semibold">
          <div className="w-[9px] h-[9px] rounded-full border-[1.5px] border-[#8b8a86]" />
          SMA (10)
        </div>
        <div className="flex items-center gap-2 border border-[#eceae6] rounded-full px-3 py-1.5 text-[11.5px] font-semibold">
          <span className="text-[#8b8a86]">$</span>Price
        </div>
        <div className="border border-[#eceae6] rounded-full px-3 py-1.5 text-[11.5px] font-semibold">1D</div>
        <button
          onClick={() => setAgentOverlay(!agentOverlay)}
          className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-[11.5px] font-bold ${
            agentOverlay ? 'bg-[#f1eeff] border border-[#ded6ff] text-[#5b46d8]' : 'border border-[#eceae6] text-[#6c6b67]'
          }`}
        >
          <div className={`w-[7px] h-[7px] rounded-[2px] rotate-45 ${agentOverlay ? 'bg-[#5b46d8]' : 'bg-[#8b8a86]'}`} />
          Agent overlay {agentOverlay ? 'on' : 'off'}
        </button>
        <div className="ms-auto flex items-center gap-1.5 text-[11px] text-[#8b8a86] font-semibold">
          Last tick {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </div>
      </div>

      <div className="flex-1 min-h-0 relative mt-2">
        <div ref={chartContainerRef} className="absolute inset-0" />

        {agentOverlay && (
          <div className="absolute left-[46%] top-[16%] flex flex-col gap-1.5 bg-[rgba(91,70,216,0.06)] border border-dashed border-[#a394f2] rounded-xl px-3 py-2 w-[190px] animate-rise pointer-events-none">
            <div className="flex items-center gap-1.5 text-[10px] font-extrabold text-[#5b46d8] tracking-wide">
              AGENT BREAKOUT ZONE
            </div>
            <div className="text-[11px] leading-[1.4] text-[#4a4945] font-medium">
              Volume-confirmed break above resistance held for 6 sessions.
            </div>
          </div>
        )}

        {agentOverlay && (
          <div className="absolute left-[62%] top-[28%] -translate-x-1/2 -translate-y-1/2 w-[11px] h-[11px] rounded-full bg-[#5b46d8] shadow-[0_0_0_5px_rgba(91,70,216,0.18)] pointer-events-none" />
        )}
      </div>

      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-[#f2f1ee]">
        <div className="flex items-center gap-2 bg-[#f4f3f0] rounded-full px-3 py-1.5 text-[11px] font-bold">Volume</div>
        <div className="flex items-center gap-2 border border-[#eceae6] rounded-full px-3 py-1.5 text-[11px] font-semibold">
          <div className="w-1.5 h-1.5 rounded-full bg-[#15161a]" />
          {stock?.code || 'VLTA'}
        </div>
        <div className="flex items-center gap-2 border border-[#eceae6] rounded-full px-3 py-1.5 text-[11px] font-semibold text-[#6c6b67]">
          <div className="w-1.5 h-1.5 rounded-full bg-[#5b46d8]" />
          Agent forecast band
        </div>
      </div>
    </div>
  );
}

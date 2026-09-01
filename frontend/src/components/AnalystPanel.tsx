'use client';

import { useState } from 'react';
import { sendAgentMessage } from '@/lib/api';
import type { StockProfile } from '@/lib/types';

interface Message {
  role: 'user' | 'agent';
  content: string;
}

interface AnalystPanelProps {
  stock: StockProfile | null;
}

export default function AnalystPanel({ stock }: AnalystPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agentOnline, setAgentOnline] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await sendAgentMessage(userMessage, { symbol: stock?.code });
      if (response.detail?.error) {
        setAgentOnline(false);
      } else if (response.response) {
        setAgentOnline(true);
        setMessages((prev) => [...prev, { role: 'agent', content: response.response! }]);
      }
    } catch {
      setAgentOnline(false);
    } finally {
      setLoading(false);
    }
  };

  const suggestedPrompts = ['Compare to sector', 'Risk if Fed holds', 'Summarize Q4 call', 'Build a thesis'];

  return (
    <div className="flex-1 min-h-0 bg-white rounded-[20px] shadow-[0_1px_2px_rgba(20,20,25,0.06)] flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#f2f1ee]">
        <div className="w-[26px] h-[26px] rounded-lg bg-[#5b46d8] flex items-center justify-center">
          <div className="w-[9px] h-[9px] bg-white rounded-[2px] rotate-45" />
        </div>
        <div className="text-[13.5px] font-extrabold">Analyst</div>
        <div className="font-mono text-[9.5px] font-semibold bg-[#f1eeff] text-[#5b46d8] rounded-md px-1.5 py-0.5">deep research</div>
        <div className="ms-auto flex items-center gap-1.5 text-[10.5px] font-semibold text-[#8b8a86]">
          <div className={`w-1.5 h-1.5 rounded-full ${agentOnline ? 'bg-[#0f8f52] animate-blink' : 'bg-[#a3a29d]'}`} />
          {agentOnline ? 'live feed' : 'coming online...'}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto px-4 py-3 flex flex-col gap-3">
        <div className="border border-[#ece9ff] bg-[#faf9ff] rounded-[14px] p-3 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[12.5px] font-extrabold">Momentum shift detected</span>
            <span className="ms-auto font-mono text-[10px] font-semibold bg-[#5b46d8] text-white rounded-md px-1.5 py-0.5">conf 78%</span>
          </div>
          <div className="text-[11.5px] leading-[1.5] text-[#4a4945] font-medium">
            {stock?.code || 'Stock'} showing technical strength. Sector peers are flat, so the move looks idiosyncratic rather than beta-driven.
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-[11px] text-[#4a4945] font-semibold">
              <div className="w-[5px] h-[5px] rounded-full bg-[#0f8f52]" />
              RSI {stock?.rsi14?.toFixed(0) || '61'} — {stock?.rsi14 && stock.rsi14 > 70 ? 'overbought' : 'rising, not yet overbought'}
            </div>
            <div className="flex items-center gap-2 text-[11px] text-[#4a4945] font-semibold">
              <div className="w-[5px] h-[5px] rounded-full bg-[#0f8f52]" />
              SMA200: {stock?.sma200_flag || 'above'} — trend supportive
            </div>
            <div className="flex items-center gap-2 text-[11px] text-[#4a4945] font-semibold">
              <div className="w-[5px] h-[5px] rounded-full bg-[#e5484d]" />
              Vol regime: {stock?.vol_regime || 'moderate'}
            </div>
          </div>
          <div className="flex gap-2 mt-0.5">
            <div className="bg-[#15161a] text-white rounded-lg px-3 py-1.5 text-[11px] font-bold cursor-pointer">Show on chart</div>
            <div className="border border-[#e3e0f7] rounded-lg px-3 py-1.5 text-[11px] font-bold text-[#5b46d8] cursor-pointer">Sources (7)</div>
          </div>
        </div>

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${
              msg.role === 'user'
                ? 'self-end max-w-[82%] bg-[#f4f3f0] rounded-[14px_14px_4px_14px]'
                : 'bg-transparent'
            } px-3 py-2`}
          >
            <div className="text-[11.5px] font-semibold leading-[1.45]">{msg.content}</div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-[11px] text-[#8b8a86]">
            <div className="w-1 h-1 rounded-full bg-[#5b46d8] animate-blink" />
            Analyzing...
          </div>
        )}

        {!agentOnline && !loading && messages.length === 0 && (
          <div className="flex flex-col gap-2">
            <div className="text-[11.5px] leading-[1.55] text-[#2c2d31] font-medium">
              Agent is coming online shortly. Ask questions about {stock?.code || 'stocks'} for AI-powered analysis.
            </div>
            <div className="flex gap-2">
              {[
                { label: 'Score', value: stock?.score?.toFixed(0) || '71' },
                { label: 'Rating', value: stock?.rating || 'Buy' },
                { label: 'P/E', value: stock?.metrics?.pe?.toFixed(1) || 'N/A' },
              ].map((m) => (
                <div key={m.label} className="flex-1 border border-[#eceae6] rounded-xl px-2.5 py-2 flex flex-col gap-0.5">
                  <div className="text-[9.5px] font-bold text-[#8b8a86] tracking-wide">{m.label}</div>
                  <div className="font-mono text-[13px] font-semibold">{m.value}</div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 text-[10.5px] text-[#8b8a86] font-semibold">
              <div className="w-1 h-1 rounded-full bg-[#c9c6bf]" />
              Data from Tadawul API
            </div>
          </div>
        )}
      </div>

      <div className="px-4 py-3 border-t border-[#f2f1ee] flex flex-col gap-2">
        <div className="flex gap-1.5 flex-wrap">
          {suggestedPrompts.map((p) => (
            <button
              key={p}
              onClick={() => setInput(p)}
              className="border border-[#eceae6] rounded-full px-3 py-1 text-[10.5px] font-semibold text-[#4a4945] hover:bg-[#f4f3f0]"
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 bg-[#f4f3f0] rounded-xl px-3 py-2.5">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={`Ask about ${stock?.code || 'stock'}...`}
            className="flex-1 bg-transparent text-[11.5px] text-[#15161a] placeholder:text-[#8b8a86] font-semibold outline-none"
          />
          <div className="ms-auto flex items-center gap-2">
            <div className="font-mono text-[9.5px] font-semibold text-[#8b8a86] bg-white rounded-md px-1.5 py-0.5">1D Tadawul</div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="w-[26px] h-[26px] rounded-lg bg-[#5b46d8] flex items-center justify-center text-white text-[12px] font-bold disabled:opacity-50"
            >
              ^
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

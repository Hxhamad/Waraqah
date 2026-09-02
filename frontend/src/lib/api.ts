import useSWR from 'swr';
import type { StockProfile, MoversData, MacroData, WatchlistItem, Alert, ScreenerResult } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8123';

const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error('API error');
    throw error;
  }
  return res.json();
};

export function useStock(symbol: string | null) {
  return useSWR<StockProfile>(
    symbol ? `${API_URL}/stock/${symbol}` : null,
    fetcher,
    { refreshInterval: 60000 }
  );
}

export function useMovers(limit = 10) {
  return useSWR<MoversData>(
    `${API_URL}/movers?limit=${limit}`,
    fetcher,
    { refreshInterval: 30000 }
  );
}

export function useMacro() {
  return useSWR<MacroData>(
    `${API_URL}/macro`,
    fetcher,
    { refreshInterval: 60000 }
  );
}

export function useWatchlist() {
  return useSWR<WatchlistItem[]>(
    `${API_URL}/watchlist`,
    fetcher,
    { refreshInterval: 30000 }
  );
}

export function useAlerts() {
  return useSWR<Alert[]>(
    `${API_URL}/alerts`,
    fetcher,
    { refreshInterval: 30000 }
  );
}

export function useScreener(params?: Record<string, string | number>) {
  const query = params ? '?' + new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)])
  ).toString() : '';
  return useSWR<ScreenerResult[]>(
    `${API_URL}/screener${query}`,
    fetcher,
    { refreshInterval: 60000 }
  );
}

export interface AgentAnswer {
  text: string;
  tools_used: string[];
  confidence: string;
  language: string;
  llm_used: boolean;
}

/**
 * POST /agent/chat and consume the SSE stream.
 * Returns the final `answer` event payload, or null if the agent failed.
 */
export async function sendAgentMessage(message: string, context?: Record<string, unknown>): Promise<AgentAnswer | null> {
  const res = await fetch(`${API_URL}/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, context }),
  });
  if (!res.ok || !res.body) return null;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';
  let answer: AgentAnswer | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() ?? '';
    for (const block of blocks) {
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ') && currentEvent === 'answer') {
          try {
            answer = JSON.parse(line.slice(6)) as AgentAnswer;
          } catch {
            /* skip malformed event */
          }
        }
      }
    }
  }
  return answer;
}

export async function addToWatchlist(symbol: string): Promise<void> {
  await fetch(`${API_URL}/watchlist/${symbol}`, { method: 'POST' });
}

export async function removeFromWatchlist(symbol: string): Promise<void> {
  await fetch(`${API_URL}/watchlist/${symbol}`, { method: 'DELETE' });
}

export async function createAlert(symbol: string, direction: 'above' | 'below', target: number): Promise<Alert> {
  const res = await fetch(`${API_URL}/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, direction, target }),
  });
  return res.json();
}

export { API_URL };

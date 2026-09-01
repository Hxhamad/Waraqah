export interface StockProfile {
  code: string;
  name: string | null;
  sector: string | null;
  price: number | null;
  returns: Record<string, number>;
  metrics: Record<string, number | null>;
  sma200_flag: string | null;
  rsi14: number | null;
  vol_regime: string | null;
  news: Array<Record<string, unknown>>;
  score: number | null;
  rating: string | null;
}

export interface Mover {
  symbol: string;
  name: string;
  price: number;
  change_pct: number;
}

export interface MoversData {
  gainers: Mover[];
  losers: Mover[];
}

export interface MacroData {
  brent: number | null;
  gold: number | null;
  usd_sar: number | null;
  btc: number | null;
  msci_ksa: number | null;
  updated_at: string | null;
}

export interface WatchlistItem {
  id: number;
  symbol: string;
  added_at: string;
}

export interface Alert {
  id: number;
  symbol: string;
  direction: string;
  target: number;
  triggered: boolean;
  created_at: string;
}

export interface AgentChatResponse {
  detail?: {
    error: string;
    spec?: string;
    message_received?: string;
  };
  response?: string;
}

export interface ScreenerResult {
  code: string;
  name: string | null;
  price: number | null;
  score: number | null;
  rating: string | null;
  change_pct?: number;
}

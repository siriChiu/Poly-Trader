/**
 * useApi — Generic API fetch hooks + fetchApi helper
 */
import { useEffect, useState, useCallback } from "react";
import { beginGlobalProgress, endGlobalProgress, updateGlobalProgress } from "./useGlobalProgress";

const RAW_BASE = (import.meta as any)?.env?.VITE_API_BASE?.trim?.() || "";
export const API_BASE = RAW_BASE.replace(/\/$/, "");

export function buildApiUrl(endpoint: string): string {
  return `${API_BASE}${endpoint}`;
}

export function buildWsUrl(path: string): string {
  if (API_BASE) {
    const httpUrl = new URL(API_BASE, window.location.origin);
    httpUrl.protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
    httpUrl.pathname = path;
    httpUrl.search = "";
    httpUrl.hash = "";
    return httpUrl.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const isViteDev = window.location.port === "5173";
  const host = isViteDev ? `${window.location.hostname}:8000` : window.location.host;
  return `${protocol}//${host}${path}`;
}

const toRequestLabel = (endpoint: string) => {
  if (endpoint.startsWith("/api/strategies/run")) return "執行策略回測請求";
  if (endpoint.startsWith("/api/strategies")) return "載入策略資料";
  if (endpoint.startsWith("/api/models/leaderboard")) return "載入模型排行榜";
  if (endpoint.startsWith("/api/chart/klines")) return "載入圖表 K 線";
  if (endpoint.startsWith("/api/features/coverage")) return "載入特徵 coverage";
  if (endpoint.startsWith("/api/features")) return "載入特徵資料";
  if (endpoint.startsWith("/api/backtest")) return "載入回測資料";
  return `載入 ${endpoint}`;
};

const API_MEMORY_CACHE = new Map<string, { data: unknown; updatedAt: number }>();

const getCachedApiResponse = <T,>(endpoint: string, maxAgeMs: number): T | null => {
  const cached = API_MEMORY_CACHE.get(endpoint);
  if (!cached) return null;
  if (Date.now() - cached.updatedAt > maxAgeMs) return null;
  return cached.data as T;
};

const setCachedApiResponse = (endpoint: string, data: unknown) => {
  API_MEMORY_CACHE.set(endpoint, { data, updatedAt: Date.now() });
};

async function fetchJsonTracked<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const taskId = beginGlobalProgress({
    kind: "network",
    tone: "blue",
    label: toRequestLabel(endpoint),
    detail: endpoint,
    progress: 0,
    priority: 10,
  });

  try {
    const resp = await fetch(buildApiUrl(endpoint), options);
    updateGlobalProgress(taskId, { progress: 45, detail: `${endpoint} · 已收到回應` });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `${resp.status}`);
    }
    const json = await resp.json();
    setCachedApiResponse(endpoint, json);
    updateGlobalProgress(taskId, { progress: 100, detail: `${endpoint} · 完成` });
    return json;
  } finally {
    endGlobalProgress(taskId);
  }
}

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  return fetchJsonTracked<T>(endpoint, options);
}

export function useApi<T>(endpoint: string, refreshMs?: number) {
  const cacheMaxAgeMs = refreshMs ? Math.max(1000, refreshMs) : 60_000;
  const [data, setData] = useState<T | null>(() => getCachedApiResponse<T>(endpoint, cacheMaxAgeMs));
  const [loading, setLoading] = useState(data == null);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    const cached = getCachedApiResponse<T>(endpoint, cacheMaxAgeMs);
    if (cached != null) {
      setData(cached);
      setLoading(false);
    } else {
      setLoading(true);
    }
    try {
      const json = await fetchJsonTracked<T>(endpoint);
      setData(json);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [endpoint, cacheMaxAgeMs]);

  useEffect(() => {
    fetch_();
    if (refreshMs) {
      const timer = setInterval(fetch_, refreshMs);
      return () => clearInterval(timer);
    }
  }, [fetch_, refreshMs]);

  return { data, loading, error, refresh: fetch_ };
}

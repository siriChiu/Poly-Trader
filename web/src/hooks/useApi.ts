/**
 * useApi — Generic API fetch hooks + fetchApi helper
 */
import { useEffect, useState, useCallback, useRef } from "react";
import { beginGlobalProgress, endGlobalProgress, updateGlobalProgress } from "./useGlobalProgress";

const RAW_BASE = (import.meta as any)?.env?.VITE_API_BASE?.trim?.() || "";
export const API_BASE = RAW_BASE.replace(/\/$/, "");
const ACTIVE_API_BASE_STORAGE_KEY = "poly_trader.active_api_base";
const DEV_LOCAL_API_CANDIDATE_PORTS = [8000, 8001] as const;
const DEFAULT_REQUEST_TIMEOUT_MS = 8000;
const CHART_REQUEST_TIMEOUT_MS = 15000;

let activeApiBaseMemo: string | null = null;

function getStoredActiveApiBase(): string | null {
  if (activeApiBaseMemo) return activeApiBaseMemo;
  if (typeof window === "undefined") return null;
  try {
    const stored = window.localStorage.getItem(ACTIVE_API_BASE_STORAGE_KEY);
    if (stored) {
      activeApiBaseMemo = stored.replace(/\/$/, "");
      return activeApiBaseMemo;
    }
  } catch {
    // Ignore localStorage access issues in strict/private contexts.
  }
  return null;
}

function persistActiveApiBase(base: string | null): void {
  activeApiBaseMemo = base ? base.replace(/\/$/, "") : null;
  if (typeof window === "undefined") return;
  try {
    if (base) {
      window.localStorage.setItem(ACTIVE_API_BASE_STORAGE_KEY, base);
    } else {
      window.localStorage.removeItem(ACTIVE_API_BASE_STORAGE_KEY);
    }
  } catch {
    // Ignore localStorage access issues in strict/private contexts.
  }
}

function isLocalDevHost(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost";
}

function getDevApiCandidateBases(): string[] {
  if (API_BASE || typeof window === "undefined") return [];
  const protocol = window.location.protocol === "https:" ? "https:" : "http:";
  const host = window.location.hostname || "127.0.0.1";
  const currentPort = Number.parseInt(window.location.port || "0", 10);
  const alreadyOnBackendPort = DEV_LOCAL_API_CANDIDATE_PORTS.includes(currentPort as (typeof DEV_LOCAL_API_CANDIDATE_PORTS)[number]);
  if (!isLocalDevHost(host) || alreadyOnBackendPort) return [];
  const preferred = getStoredActiveApiBase();
  const candidates = DEV_LOCAL_API_CANDIDATE_PORTS.map((port) => `${protocol}//${host}:${port}`);
  if (preferred && candidates.includes(preferred)) {
    return [preferred, ...candidates.filter((candidate) => candidate !== preferred)];
  }
  return candidates;
}

function buildApiUrlForBase(endpoint: string, base: string | null): string {
  return base ? `${base}${endpoint}` : endpoint;
}

function getApiRequestCandidates(): string[] {
  if (API_BASE) return [API_BASE];
  const devCandidates = getDevApiCandidateBases();
  if (devCandidates.length) return devCandidates;
  const preferred = getStoredActiveApiBase();
  return [preferred ?? ""];
}

function getRequestTimeoutMs(endpoint: string): number {
  return endpoint.startsWith("/api/chart/klines")
    ? CHART_REQUEST_TIMEOUT_MS
    : DEFAULT_REQUEST_TIMEOUT_MS;
}

function attachAbortSignal(controller: AbortController, signal?: AbortSignal): (() => void) | null {
  if (!signal) return null;
  if (signal.aborted) {
    controller.abort(signal.reason);
    return null;
  }
  const relayAbort = () => controller.abort(signal.reason);
  signal.addEventListener("abort", relayAbort, { once: true });
  return () => signal.removeEventListener("abort", relayAbort);
}

export function buildApiUrl(endpoint: string): string {
  const preferredBase = API_BASE || getStoredActiveApiBase();
  return buildApiUrlForBase(endpoint, preferredBase);
}

function toWebSocketUrl(base: string | null, path: string): string {
  if (base) {
    const httpUrl = new URL(base, window.location.origin);
    httpUrl.protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
    httpUrl.pathname = path;
    httpUrl.search = "";
    httpUrl.hash = "";
    return httpUrl.toString();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

export function buildWsCandidateUrls(path: string): string[] {
  const preferredBase = API_BASE || getStoredActiveApiBase();
  const devCandidates = !API_BASE ? getDevApiCandidateBases() : [];
  if (preferredBase) {
    const fallbackCandidates = devCandidates.filter((candidate) => candidate !== preferredBase);
    return [toWebSocketUrl(preferredBase, path), ...fallbackCandidates.map((candidate) => toWebSocketUrl(candidate, path))];
  }
  if (devCandidates.length) {
    return devCandidates.map((candidate) => toWebSocketUrl(candidate, path));
  }
  return [toWebSocketUrl(preferredBase, path)];
}

export function rememberActiveApiBaseFromWsUrl(wsUrl: string): void {
  try {
    const url = new URL(wsUrl, window.location.origin);
    url.protocol = url.protocol === "wss:" ? "https:" : "http:";
    url.pathname = "";
    url.search = "";
    url.hash = "";
    persistActiveApiBase(url.toString().replace(/\/$/, ""));
  } catch {
    // Ignore invalid WS URLs and leave the current active base untouched.
  }
}

export function buildWsUrl(path: string): string {
  return buildWsCandidateUrls(path)[0];
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

function formatApiErrorDetail(detail: unknown): string {
  if (detail == null) return "API 錯誤";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => formatApiErrorDetail(item)).filter(Boolean).join("; ");
  }
  if (typeof detail === "object") {
    const payload = detail as Record<string, unknown>;
    const code = typeof payload.code === "string" ? payload.code : null;
    const message = typeof payload.message === "string" ? payload.message : null;
    if (code || message) {
      return [code ? `[${code}]` : null, message].filter(Boolean).join(" ");
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    try {
      return JSON.stringify(payload);
    } catch {
      return "API 錯誤";
    }
  }
  return String(detail);
}

const getCachedApiResponse = <T,>(endpoint: string, maxAgeMs: number): T | null => {
  const cached = API_MEMORY_CACHE.get(endpoint);
  if (!cached) return null;
  if (Date.now() - cached.updatedAt > maxAgeMs) return null;
  return cached.data as T;
};

const setCachedApiResponse = (endpoint: string, data: unknown) => {
  API_MEMORY_CACHE.set(endpoint, { data, updatedAt: Date.now() });
};

async function fetchTrackedResponse(endpoint: string, options?: RequestInit): Promise<Response> {
  const taskId = beginGlobalProgress({
    kind: "network",
    tone: "blue",
    label: toRequestLabel(endpoint),
    detail: endpoint,
    progress: 0,
    priority: 10,
  });

  try {
    const requestCandidates = getApiRequestCandidates();
    const method = String(options?.method || "GET").toUpperCase();
    const canFallback = !API_BASE && requestCandidates.length > 1 && ["GET", "HEAD"].includes(method);
    let lastError: Error | null = null;

    for (let index = 0; index < requestCandidates.length; index += 1) {
      const base = requestCandidates[index];
      const requestUrl = buildApiUrlForBase(endpoint, base);
      const controller = new AbortController();
      const detachAbort = attachAbortSignal(controller, options?.signal ?? undefined);
      const timeoutMs = getRequestTimeoutMs(endpoint);
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

      try {
        const resp = await fetch(requestUrl, { ...options, signal: controller.signal });
        if (base) persistActiveApiBase(base);
        updateGlobalProgress(taskId, { progress: 45, detail: `${endpoint} · 已收到回應` });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: resp.statusText }));
          throw new Error(formatApiErrorDetail(err.detail ?? err) || `${resp.status}`);
        }
        updateGlobalProgress(taskId, { progress: 100, detail: `${endpoint} · 完成` });
        return resp;
      } catch (error: any) {
        const isTimeout = controller.signal.aborted && !options?.signal?.aborted;
        const isNetworkError = error instanceof TypeError;
        const normalizedError = isTimeout
          ? Object.assign(new Error(`API timeout after ${timeoutMs}ms`), { name: "AbortError" })
          : (error instanceof Error ? error : new Error(String(error)));

        if ((isTimeout || isNetworkError) && base === getStoredActiveApiBase()) {
          persistActiveApiBase(null);
        }
        lastError = normalizedError;

        const canRetryCurrent = canFallback && index < requestCandidates.length - 1 && (isTimeout || isNetworkError);
        if (canRetryCurrent) {
          const nextBase = requestCandidates[index + 1];
          updateGlobalProgress(taskId, {
            progress: 20,
            detail: `${endpoint} · ${base || "same-origin"} 無回應，改試 ${nextBase || "same-origin"}`,
          });
          continue;
        }
        throw normalizedError;
      } finally {
        window.clearTimeout(timeoutId);
        detachAbort?.();
      }
    }

    throw lastError ?? new Error(`Failed to fetch ${endpoint}`);
  } finally {
    endGlobalProgress(taskId);
  }
}

async function fetchJsonTracked<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const resp = await fetchTrackedResponse(endpoint, options);
  const json = await resp.json();
  setCachedApiResponse(endpoint, json);
  return json;
}

export async function fetchApiResponse(endpoint: string, options?: RequestInit): Promise<Response> {
  return fetchTrackedResponse(endpoint, options);
}

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  return fetchJsonTracked<T>(endpoint, options);
}

export function useApi<T>(endpoint: string, refreshMs?: number) {
  const cacheMaxAgeMs = refreshMs ? Math.max(1000, refreshMs) : 60_000;
  const [data, setData] = useState<T | null>(() => getCachedApiResponse<T>(endpoint, cacheMaxAgeMs));
  const [loading, setLoading] = useState(data == null);
  const [error, setError] = useState<string | null>(null);
  const requestSeqRef = useRef(0);
  const activeControllerRef = useRef<AbortController | null>(null);

  const cancelActiveRequest = useCallback(() => {
    requestSeqRef.current += 1;
    activeControllerRef.current?.abort();
    activeControllerRef.current = null;
  }, []);

  const fetch_ = useCallback(async () => {
    requestSeqRef.current += 1;
    const requestSeq = requestSeqRef.current;
    activeControllerRef.current?.abort();
    const controller = new AbortController();
    activeControllerRef.current = controller;

    const cached = getCachedApiResponse<T>(endpoint, cacheMaxAgeMs);
    if (cached != null) {
      setData(cached);
      setError(null);
      setLoading(false);
    } else {
      setError(null);
      setLoading(true);
    }

    try {
      const json = await fetchJsonTracked<T>(endpoint, { signal: controller.signal });
      if (controller.signal.aborted || requestSeq !== requestSeqRef.current) return;
      setData(json);
      setError(null);
    } catch (e: any) {
      if (controller.signal.aborted || requestSeq !== requestSeqRef.current) return;
      setError(e?.message || String(e));
    } finally {
      if (activeControllerRef.current === controller) {
        activeControllerRef.current = null;
      }
      if (!controller.signal.aborted && requestSeq === requestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [endpoint, cacheMaxAgeMs]);

  useEffect(() => {
    fetch_();
    if (refreshMs) {
      const timer = setInterval(fetch_, refreshMs);
      return () => {
        clearInterval(timer);
        cancelActiveRequest();
      };
    }
    return () => {
      cancelActiveRequest();
    };
  }, [cancelActiveRequest, fetch_, refreshMs]);

  return { data, loading, error, refresh: fetch_ };
}

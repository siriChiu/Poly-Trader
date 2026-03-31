/**
 * useApi — Generic API fetch hooks + fetchApi helper
 */
import { useEffect, useState, useCallback } from "react";

const BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${endpoint}`, options);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `${resp.status}`);
  }
  return resp.json();
}

export function useApi<T>(endpoint: string, refreshMs?: number) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const resp = await fetch(`${BASE}${endpoint}`);
      if (!resp.ok) throw new Error(`${resp.status}`);
      const json = await resp.json();
      setData(json);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    fetch_();
    if (refreshMs) {
      const timer = setInterval(fetch_, refreshMs);
      return () => clearInterval(timer);
    }
  }, [fetch_, refreshMs]);

  return { data, loading, error, refresh: fetch_ };
}

/**
 * useApi — Generic API fetch hooks
 */
import { useEffect, useState, useCallback } from "react";

const BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

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

export function useApiPost<T>(endpoint: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const post = async (body: any) => {
    setLoading(true);
    try {
      const resp = await fetch(`${BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await resp.json();
      if (!resp.ok) throw new Error(json.detail || `${resp.status}`);
      setData(json);
      setError(null);
      return json;
    } catch (e: any) {
      setError(e.message);
      return { error: e.message };
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, post };
}

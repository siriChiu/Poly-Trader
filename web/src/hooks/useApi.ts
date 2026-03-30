import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API 請求失敗')
  }
  return res.json()
}

export function useApi<T>(path: string, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<T>(path)
      setData(result)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    refetch()
  }, [refetch, ...deps])

  return { data, loading, error, refetch }
}

export function useApiPost<T>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const post = useCallback(async (path: string, body?: any): Promise<T | null> => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<T>(path, {
        method: 'POST',
        body: body ? JSON.stringify(body) : undefined,
      })
      return result
    } catch (e: any) {
      setError(e.message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { post, loading, error }
}

export { fetchApi }

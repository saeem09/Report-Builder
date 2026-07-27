import { useCallback, useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'

export type AsyncStatus = 'loading' | 'ready' | 'error'

export type AsyncResource<T> = {
  data: T | null
  status: AsyncStatus
  error: unknown
  /** Re-run the loader. Used after an operation the server owns entirely. */
  reload: () => void
  /**
   * Replace the data without a request. This is the main path after a
   * mutation: the API returns the authoritative object, so refetching it would
   * be a second round trip for an answer already in hand.
   *
   * Accepts either a plain value or a `(prev) => next` updater, matching
   * React's own useState setter overload. When a caller derives the next
   * value from the current one -- e.g. replacing one field inside a larger
   * object -- the updater form must be used instead of closing over a value
   * from the render that scheduled the mutation. Two mutations started close
   * together (e.g. two independent saves) can otherwise both close over the
   * same pre-mutation snapshot; whichever resolves last then silently
   * reverts the other's already-applied change.
   */
  setData: Dispatch<SetStateAction<T | null>>
}

/**
 * Load one resource on mount and expose its loading, ready, and error states.
 *
 * IMPORTANT: load must be referentially stable. It is an effect dependency, so
 * an inline arrow function creates a new identity on every render and turns
 * this into an infinite request loop. Always wrap it at the call site:
 *
 *   const load = useCallback(() => getReport(reportId), [reportId])
 *   const { data, status } = useAsyncResource(load)
 *
 * The isCurrent flag discards a response that arrives after the effect has
 * been cleaned up, which happens on unmount, on a reload that supersedes an
 * in-flight request, and on every StrictMode double-mount in development.
 */
export function useAsyncResource<T>(load: () => Promise<T>): AsyncResource<T> {
  const [data, setData] = useState<T | null>(null)
  const [status, setStatus] = useState<AsyncStatus>('loading')
  const [error, setError] = useState<unknown>(null)
  const [reloadCount, setReloadCount] = useState(0)

  const reload = useCallback(() => {
    setReloadCount((count) => count + 1)
  }, [])

  useEffect(() => {
    let isCurrent = true
    setStatus('loading')
    setError(null)
    load()
      .then((result) => {
        if (!isCurrent) {
          return
        }
        setData(result)
        setStatus('ready')
      })
      .catch((caught: unknown) => {
        if (!isCurrent) {
          return
        }
        setError(caught)
        setStatus('error')
      })
    return () => {
      isCurrent = false
    }
  }, [load, reloadCount])

  return { data, status, error, reload, setData }
}

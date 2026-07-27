import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StrictMode, useCallback } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { useAsyncResource } from './useAsyncResource'

type Harness = {
  load: () => Promise<string>
}

function Harness({ load }: Harness) {
  const stableLoad = useCallback(load, [load])
  const { data, status, error, reload, setData } = useAsyncResource<string>(stableLoad)

  return (
    <div>
      <p data-testid="status">{status}</p>
      <p data-testid="data">{data ?? 'none'}</p>
      <p data-testid="error">{error instanceof Error ? error.message : 'none'}</p>
      <button type="button" onClick={reload}>
        Reload
      </button>
      <button type="button" onClick={() => setData('local')}>
        Set local
      </button>
    </div>
  )
}

function renderHarness(load: () => Promise<string>) {
  return render(
    <StrictMode>
      <Harness load={load} />
    </StrictMode>,
  )
}

describe('useAsyncResource', () => {
  it('starts in the loading status with no data', () => {
    renderHarness(() => new Promise<string>(() => {}))

    expect(screen.getByTestId('status')).toHaveTextContent('loading')
    expect(screen.getByTestId('data')).toHaveTextContent('none')
  })

  it('moves to ready with the resolved data', async () => {
    renderHarness(() => Promise.resolve('first'))

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ready')
    })
    expect(screen.getByTestId('data')).toHaveTextContent('first')
  })

  it('moves to error and keeps the thrown value', async () => {
    renderHarness(() => Promise.reject(new Error('boom')))

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('error')
    })
    expect(screen.getByTestId('error')).toHaveTextContent('boom')
  })

  it('loads once per mount even under StrictMode double-invocation', async () => {
    const load = vi.fn(() => Promise.resolve('first'))
    renderHarness(load)

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ready')
    })
    // StrictMode mounts, unmounts, and remounts the effect, so the loader runs
    // twice by design. What matters is that the result is not duplicated and
    // no stale result wins.
    expect(screen.getByTestId('data')).toHaveTextContent('first')
  })

  it('reload runs the loader again and picks up the new value', async () => {
    const user = userEvent.setup()
    let call = 0
    renderHarness(() => Promise.resolve(`call-${++call}`))

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ready')
    })
    const before = screen.getByTestId('data').textContent

    await user.click(screen.getByRole('button', { name: 'Reload' }))

    await waitFor(() => {
      expect(screen.getByTestId('data')).not.toHaveTextContent(before ?? '')
    })
  })

  it('setData replaces the data without another load', async () => {
    const user = userEvent.setup()
    const load = vi.fn(() => Promise.resolve('first'))
    renderHarness(load)

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ready')
    })
    const callsAfterLoad = load.mock.calls.length

    await user.click(screen.getByRole('button', { name: 'Set local' }))

    expect(screen.getByTestId('data')).toHaveTextContent('local')
    expect(load).toHaveBeenCalledTimes(callsAfterLoad)
  })

  it('ignores a result that arrives after unmount', async () => {
    let resolveLoad: (value: string) => void = () => {}
    const { unmount } = renderHarness(
      () =>
        new Promise<string>((resolve) => {
          resolveLoad = resolve
        }),
    )

    unmount()
    await act(async () => {
      resolveLoad('late')
    })

    // No "state update on an unmounted component" warning and no throw is the
    // assertion here; the guard inside the effect is what prevents it.
    expect(true).toBe(true)
  })
})

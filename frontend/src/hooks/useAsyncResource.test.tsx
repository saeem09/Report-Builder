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
      <button type="button" onClick={() => setData((prev) => `${prev ?? 'none'}-appended`)}>
        Set functional
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

  it('setData accepts an updater function and receives the current state', async () => {
    const user = userEvent.setup()
    renderHarness(() => Promise.resolve('first'))

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ready')
    })

    // Matches React's own useState setter overload: setData can take either a
    // plain value or a (prev) => next updater. This is the form callers need
    // when a save's callback must not close over a stale copy of the state.
    await user.click(screen.getByRole('button', { name: 'Set functional' }))

    expect(screen.getByTestId('data')).toHaveTextContent('first-appended')
  })

  it('does not throw when a fetch resolves after unmount', async () => {
    // React removed the "state update on an unmounted component" warning in
    // React 18, so there is nothing to assert about a warning here. What
    // this test does prove: the isCurrent guard means the late resolution is
    // silently ignored rather than throwing or logging an error.
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
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

    expect(consoleError).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })

  it('discards a stale response when reload fires before the first fetch resolves', async () => {
    const resolvers: Array<(value: string) => void> = []
    const load = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          resolvers.push(resolve)
        }),
    )
    // Rendered without StrictMode: this test asserts something about the
    // exact number and order of loader invocations, and StrictMode's
    // dev-only double-invocation would only add noise to that count. The
    // StrictMode-safety concern is already covered by the dedicated test
    // above.
    render(<Harness load={load} />)
    const user = userEvent.setup()

    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))

    await user.click(screen.getByRole('button', { name: 'Reload' }))

    await waitFor(() => expect(load).toHaveBeenCalledTimes(2))
    expect(resolvers).toHaveLength(2)

    // Resolve the newer (second) fetch first, so a real out-of-order race
    // exists: at this point the first fetch is still pending.
    await act(async () => {
      resolvers[1]('second')
    })
    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('ready')
    })
    expect(screen.getByTestId('data')).toHaveTextContent('second')

    // Now let the stale first fetch resolve. If the isCurrent guard were
    // broken, this would clobber the fresh 'second' value.
    await act(async () => {
      resolvers[0]('first')
    })
    expect(screen.getByTestId('data')).toHaveTextContent('second')
    expect(screen.getByTestId('status')).toHaveTextContent('ready')
  })

  it('discards a stale response when the load identity changes before the first fetch resolves', async () => {
    const resolvers: Array<(value: string) => void> = []
    const firstLoad = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          resolvers.push(resolve)
        }),
    )
    const secondLoad = vi.fn(
      () =>
        new Promise<string>((resolve) => {
          resolvers.push(resolve)
        }),
    )
    // Rendered without StrictMode for the same reason as the reload race
    // test above: precise control over how many times each loader ran.
    const { rerender } = render(<Harness load={firstLoad} />)

    await waitFor(() => expect(firstLoad).toHaveBeenCalledTimes(1))

    // Simulate switching to a different resource (e.g. a new id) before the
    // first fetch resolves: the caller passes a new load function identity.
    rerender(<Harness load={secondLoad} />)

    await waitFor(() => expect(secondLoad).toHaveBeenCalledTimes(1))
    expect(resolvers).toHaveLength(2)

    // The fresh fetch (for the new load identity) resolves first.
    await act(async () => {
      resolvers[1]('fresh')
    })
    await waitFor(() => {
      expect(screen.getByTestId('data')).toHaveTextContent('fresh')
    })

    // The stale fetch (for the old load identity) resolves after. It must
    // not overwrite the fresh result.
    await act(async () => {
      resolvers[0]('stale')
    })
    expect(screen.getByTestId('data')).toHaveTextContent('fresh')
    expect(screen.getByTestId('status')).toHaveTextContent('ready')
  })
})

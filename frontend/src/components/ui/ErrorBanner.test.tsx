import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, NetworkError } from '../../api/client'
import { ErrorBanner, toUserMessage } from './ErrorBanner'

describe('toUserMessage', () => {
  it.each([
    [400, 'That request was rejected. Check the file or the values you entered.'],
    [404, 'That report or field no longer exists. Return to the reports list.'],
    [409, 'Upload at least one source document before generating content.'],
    [413, 'That file is too large. The limit is 10 MB.'],
    [422, 'Some values are not valid. Check the highlighted fields.'],
    [500, 'The server could not complete that request. Try again.'],
    [502, 'The AI service could not draft this report. Please try again.'],
  ])('maps status %i to fixed copy', (status, expected) => {
    expect(toUserMessage(new ApiError(status, 'raw server detail'))).toBe(expected)
  })

  it('falls back to the server detail for an unmapped status', () => {
    expect(toUserMessage(new ApiError(418, 'I am a teapot'))).toBe('I am a teapot')
  })

  it('passes a NetworkError message through', () => {
    expect(toUserMessage(new NetworkError('Could not reach the server.'))).toBe(
      'Could not reach the server.',
    )
  })

  it('never leaks an unexpected throwable', () => {
    expect(toUserMessage(new TypeError('undefined is not a function'))).toBe(
      'Something went wrong. Please try again.',
    )
    expect(toUserMessage('a bare string')).toBe('Something went wrong. Please try again.')
  })
})

describe('ErrorBanner', () => {
  it('renders nothing when there is no error', () => {
    const { container } = render(<ErrorBanner error={null} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('renders the mapped message in an alert region', () => {
    render(<ErrorBanner error={new ApiError(409, 'no sources')} />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Upload at least one source document before generating content.',
    )
  })

  it('shows no dismiss control when onDismiss is omitted', () => {
    render(<ErrorBanner error={new ApiError(500, 'boom')} />)

    expect(screen.queryByRole('button', { name: 'Dismiss error' })).toBeNull()
  })

  it('calls onDismiss when the dismiss control is used', async () => {
    const user = userEvent.setup()
    const onDismiss = vi.fn()
    render(<ErrorBanner error={new ApiError(500, 'boom')} onDismiss={onDismiss} />)

    await user.click(screen.getByRole('button', { name: 'Dismiss error' }))

    expect(onDismiss).toHaveBeenCalledTimes(1)
  })
})

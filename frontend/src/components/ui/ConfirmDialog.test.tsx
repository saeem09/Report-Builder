import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ConfirmDialog } from './ConfirmDialog'

function renderDialog(overrides: Partial<Parameters<typeof ConfirmDialog>[0]> = {}) {
  const props = {
    title: 'Delete this report',
    message: 'This removes the report and all of its fields. It cannot be undone.',
    confirmLabel: 'Delete report',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  }
  render(<ConfirmDialog {...props} />)
  return props
}

describe('ConfirmDialog', () => {
  it('renders a modal dialog labelled by its title', () => {
    renderDialog()

    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAccessibleName('Delete this report')
    expect(
      screen.getByText(
        'This removes the report and all of its fields. It cannot be undone.',
      ),
    ).toBeInTheDocument()
  })

  it('focuses Cancel so the safe choice is the default', () => {
    renderDialog()

    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('calls onConfirm when the confirm control is used', async () => {
    const user = userEvent.setup()
    const props = renderDialog()

    await user.click(screen.getByRole('button', { name: 'Delete report' }))

    expect(props.onConfirm).toHaveBeenCalledTimes(1)
    expect(props.onCancel).not.toHaveBeenCalled()
  })

  it('calls onCancel when Cancel is used', async () => {
    const user = userEvent.setup()
    const props = renderDialog()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(props.onCancel).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel on Escape', async () => {
    const user = userEvent.setup()
    const props = renderDialog()

    await user.keyboard('{Escape}')

    expect(props.onCancel).toHaveBeenCalledTimes(1)
  })
})

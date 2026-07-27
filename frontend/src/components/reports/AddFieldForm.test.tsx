import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import * as reportsApi from '../../api/reports'
import { makeField } from '../../test/fixtures'
import { AddFieldForm } from './AddFieldForm'

describe('AddFieldForm', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('adds a field and hands the new field up', async () => {
    const user = userEvent.setup()
    const created = makeField('f9', 'Next steps')
    const add = vi.spyOn(reportsApi, 'addField').mockResolvedValue(created)
    const onAdded = vi.fn()
    render(<AddFieldForm reportId="r1" onAdded={onAdded} />)

    await user.type(screen.getByLabelText('New field label'), 'Next steps')
    await user.click(screen.getByRole('button', { name: 'Add field' }))

    await waitFor(() => {
      expect(add).toHaveBeenCalledWith('r1', 'Next steps')
    })
    expect(onAdded).toHaveBeenCalledWith(created)
  })

  it('clears the input after a successful add', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'addField').mockResolvedValue(makeField('f9', 'Next steps'))
    render(<AddFieldForm reportId="r1" onAdded={vi.fn()} />)

    await user.type(screen.getByLabelText('New field label'), 'Next steps')
    await user.click(screen.getByRole('button', { name: 'Add field' }))

    await waitFor(() => {
      expect(screen.getByLabelText('New field label')).toHaveValue('')
    })
  })

  it('trims the label before sending it', async () => {
    const user = userEvent.setup()
    const add = vi
      .spyOn(reportsApi, 'addField')
      .mockResolvedValue(makeField('f9', 'Next steps'))
    render(<AddFieldForm reportId="r1" onAdded={vi.fn()} />)

    await user.type(screen.getByLabelText('New field label'), '  Next steps  ')
    await user.click(screen.getByRole('button', { name: 'Add field' }))

    await waitFor(() => {
      expect(add).toHaveBeenCalledWith('r1', 'Next steps')
    })
  })

  it('keeps the submit control disabled for a blank label', async () => {
    const user = userEvent.setup()
    render(<AddFieldForm reportId="r1" onAdded={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Add field' })).toBeDisabled()

    await user.type(screen.getByLabelText('New field label'), '   ')

    expect(screen.getByRole('button', { name: 'Add field' })).toBeDisabled()
  })

  it('surfaces a server failure and keeps the typed label', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'addField').mockRejectedValue(new ApiError(404, 'gone'))
    render(<AddFieldForm reportId="r1" onAdded={vi.fn()} />)

    await user.type(screen.getByLabelText('New field label'), 'Next steps')
    await user.click(screen.getByRole('button', { name: 'Add field' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That report or field no longer exists. Return to the reports list.',
    )
    expect(screen.getByLabelText('New field label')).toHaveValue('Next steps')
  })

  it('caps the label at the server limit of 200 characters', () => {
    render(<AddFieldForm reportId="r1" onAdded={vi.fn()} />)

    expect(screen.getByLabelText('New field label')).toHaveAttribute('maxLength', '200')
  })
})

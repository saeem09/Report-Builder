import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import * as reportsApi from '../../api/reports'
import type { ReportDetail } from '../../api/types'
import { CreateReportForm } from './CreateReportForm'

const REPORT: ReportDetail = {
  id: 'r1',
  name: 'Kickoff',
  logo_file_id: null,
  created_at: '2026-07-27T10:00:00.000000Z',
  updated_at: '2026-07-27T10:00:00.000000Z',
  fields: [],
}

describe('CreateReportForm', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates a report with the name and no labels', async () => {
    const user = userEvent.setup()
    const create = vi.spyOn(reportsApi, 'createReport').mockResolvedValue(REPORT)
    const onCreated = vi.fn()
    render(<CreateReportForm onCreated={onCreated} />)

    await user.type(screen.getByLabelText('Report name'), 'Kickoff')
    await user.click(screen.getByRole('button', { name: 'Create report' }))

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith('Kickoff', [])
    })
    expect(onCreated).toHaveBeenCalledWith(REPORT)
  })

  it('splits initial field labels on newlines, trimming and dropping blanks', async () => {
    const user = userEvent.setup()
    const create = vi.spyOn(reportsApi, 'createReport').mockResolvedValue(REPORT)
    render(<CreateReportForm onCreated={vi.fn()} />)

    await user.type(screen.getByLabelText('Report name'), 'Kickoff')
    await user.type(
      screen.getByLabelText('Initial field labels (one per line, optional)'),
      '  Summary  \n\n Blockers \n',
    )
    await user.click(screen.getByRole('button', { name: 'Create report' }))

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith('Kickoff', ['Summary', 'Blockers'])
    })
  })

  it('refuses to submit a blank name and does not call the api', async () => {
    const user = userEvent.setup()
    const create = vi.spyOn(reportsApi, 'createReport')
    render(<CreateReportForm onCreated={vi.fn()} />)

    await user.type(screen.getByLabelText('Report name'), '   ')
    await user.click(screen.getByRole('button', { name: 'Create report' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Enter a name for this report.',
    )
    expect(create).not.toHaveBeenCalled()
  })

  it('disables the submit control while the request is in flight', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'createReport').mockReturnValue(new Promise(() => {}))
    render(<CreateReportForm onCreated={vi.fn()} />)

    await user.type(screen.getByLabelText('Report name'), 'Kickoff')
    await user.click(screen.getByRole('button', { name: 'Create report' }))

    expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled()
  })

  it('surfaces a server validation failure and re-enables the form', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'createReport').mockRejectedValue(
      new ApiError(422, 'Value error, must not be blank'),
    )
    const onCreated = vi.fn()
    render(<CreateReportForm onCreated={onCreated} />)

    await user.type(screen.getByLabelText('Report name'), 'Kickoff')
    await user.click(screen.getByRole('button', { name: 'Create report' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Some values are not valid. Check the highlighted fields.',
    )
    expect(onCreated).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Create report' })).toBeEnabled()
  })

  it('caps the name at the server limit of 200 characters', () => {
    render(<CreateReportForm onCreated={vi.fn()} />)

    expect(screen.getByLabelText('Report name')).toHaveAttribute('maxLength', '200')
  })
})

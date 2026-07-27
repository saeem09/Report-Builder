import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import * as reportsApi from '../api/reports'
import { makeField, makeReport } from '../test/fixtures'
import { ReportDetailPage } from './ReportDetailPage'

function renderDetailPage() {
  return render(
    <MemoryRouter initialEntries={['/reports/r1']}>
      <Routes>
        <Route path="/reports/:reportId" element={<ReportDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ReportDetailPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading message before the report arrives', () => {
    vi.spyOn(reportsApi, 'getReport').mockReturnValue(new Promise(() => {}))
    renderDetailPage()

    expect(screen.getByText('Loading report...')).toBeInTheDocument()
  })

  it('requests the report id from the route', async () => {
    const get = vi.spyOn(reportsApi, 'getReport').mockResolvedValue(makeReport())
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    expect(get).toHaveBeenCalledWith('r1')
  })

  it('shows the fields in order with their labels and content', async () => {
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', { content: 'We shipped the parser.', sort_order: 0 }),
          makeField('f2', 'Blockers', { content: 'None.', sort_order: 1 }),
        ],
      }),
    )
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    const labels = screen.getAllByTestId('field-label').map((node) => node.textContent)
    expect(labels).toEqual(['Summary', 'Blockers'])
    expect(screen.getByText('We shipped the parser.')).toBeInTheDocument()
    expect(screen.getByText('None.')).toBeInTheDocument()
  })

  it('shows an empty state when the report has no fields', async () => {
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(makeReport())
    renderDetailPage()

    expect(
      await screen.findByText('This report has no fields yet.'),
    ).toBeInTheDocument()
  })

  it('shows the not-found message for a missing report', async () => {
    vi.spyOn(reportsApi, 'getReport').mockRejectedValue(new ApiError(404, 'missing'))
    renderDetailPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That report or field no longer exists. Return to the reports list.',
    )
  })

  it('offers a way back to the list', async () => {
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(makeReport())
    renderDetailPage()

    expect(await screen.findByRole('link', { name: 'Back to reports' })).toHaveAttribute(
      'href',
      '/reports',
    )
  })

  it('replaces only the saved field in place after an edit', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', { sort_order: 0 }),
          makeField('f2', 'Blockers', { content: 'None.', sort_order: 1 }),
        ],
      }),
    )
    vi.spyOn(reportsApi, 'updateFieldContent').mockResolvedValue(
      makeField('f1', 'Summary', {
        content: 'Mine.',
        sort_order: 0,
        is_user_edited: true,
      }),
    )
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    await user.type(screen.getByLabelText('Summary content'), 'Mine.')
    await user.click(screen.getAllByRole('button', { name: 'Save' })[0])

    await waitFor(() => {
      expect(screen.getByText('Edited by you')).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Blockers content')).toHaveValue('None.')
    expect(
      screen.getAllByTestId('field-label').map((node) => node.textContent),
    ).toEqual(['Summary', 'Blockers'])
  })
})

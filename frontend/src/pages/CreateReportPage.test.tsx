import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as reportsApi from '../api/reports'
import type { ReportDetail } from '../api/types'
import { CreateReportPage } from './CreateReportPage'

const REPORT: ReportDetail = {
  id: 'r1',
  name: 'Kickoff',
  logo_file_id: null,
  created_at: '2026-07-27T10:00:00.000000Z',
  updated_at: '2026-07-27T10:00:00.000000Z',
  fields: [],
}

describe('CreateReportPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('navigates to the new report after it is created', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'createReport').mockResolvedValue(REPORT)

    render(
      <MemoryRouter initialEntries={['/reports/new']}>
        <Routes>
          <Route path="/reports/new" element={<CreateReportPage />} />
          <Route path="/reports/:reportId" element={<p>Detail for r1</p>} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText('Report name'), 'Kickoff')
    await user.click(screen.getByRole('button', { name: 'Create report' }))

    expect(await screen.findByText('Detail for r1')).toBeInTheDocument()
  })

  it('offers a way back to the list', () => {
    render(
      <MemoryRouter>
        <CreateReportPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Back to reports' })).toHaveAttribute(
      'href',
      '/reports',
    )
  })
})

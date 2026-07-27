import { render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, NetworkError } from '../api/client'
import * as reportsApi from '../api/reports'
import type { ReportSummary } from '../api/types'
import { ReportsListPage } from './ReportsListPage'

function makeSummary(id: string, name: string): ReportSummary {
  return {
    id,
    name,
    logo_file_id: null,
    created_at: '2026-07-27T10:00:00.000000Z',
    updated_at: '2026-07-27T10:05:00.000000Z',
  }
}

function renderPage() {
  return render(
    <StrictMode>
      <MemoryRouter>
        <ReportsListPage />
      </MemoryRouter>
    </StrictMode>,
  )
}

describe('ReportsListPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading message before the request settles', () => {
    vi.spyOn(reportsApi, 'listReports').mockReturnValue(new Promise(() => {}))
    renderPage()

    expect(screen.getByText('Loading reports...')).toBeInTheDocument()
  })

  it('links each report to its detail page', async () => {
    vi.spyOn(reportsApi, 'listReports').mockResolvedValue([
      makeSummary('r1', 'Kickoff'),
      makeSummary('r2', 'Retro'),
    ])
    renderPage()

    expect(await screen.findByRole('link', { name: 'Kickoff' })).toHaveAttribute(
      'href',
      '/reports/r1',
    )
    expect(screen.getByRole('link', { name: 'Retro' })).toHaveAttribute(
      'href',
      '/reports/r2',
    )
  })

  it('shows when each report was last updated', async () => {
    vi.spyOn(reportsApi, 'listReports').mockResolvedValue([
      makeSummary('r1', 'Kickoff'),
    ])
    renderPage()

    await screen.findByRole('link', { name: 'Kickoff' })
    expect(screen.getByTestId('updated-r1')).toHaveTextContent(/^Updated /)
  })

  it('offers a link to create a new report', async () => {
    vi.spyOn(reportsApi, 'listReports').mockResolvedValue([])
    renderPage()

    expect(screen.getByRole('link', { name: 'New report' })).toHaveAttribute(
      'href',
      '/reports/new',
    )
  })

  it('shows the empty state when the server returns no reports', async () => {
    vi.spyOn(reportsApi, 'listReports').mockResolvedValue([])
    renderPage()

    expect(await screen.findByText('No reports yet.')).toBeInTheDocument()
  })

  it('shows an error banner when the request fails', async () => {
    vi.spyOn(reportsApi, 'listReports').mockRejectedValue(new ApiError(500, 'boom'))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The server could not complete that request. Try again.',
    )
  })

  it('shows the offline message when the backend is unreachable', async () => {
    vi.spyOn(reportsApi, 'listReports').mockRejectedValue(
      new NetworkError('Could not reach the server. Check that the backend is running.'),
    )
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not reach the server. Check that the backend is running.',
    )
  })
})

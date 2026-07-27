import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import * as reportsApi from '../api/reports'
import type { ReportField } from '../api/types'
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

  it('keeps both fields updated when a later save resolves before an earlier one', async () => {
    // Regression test for the lost-update race: each ReportFieldCard's
    // onSaved used to close over the `report` value from its own render. If
    // field A's save is started, then field B's save is started before A's
    // PATCH resolves, and B's promise resolves first, A's eventual
    // resolution would overwrite state built from a report that pre-dates
    // B's edit -- silently reverting B in the UI even though the server
    // still has B's correct value.
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', { content: 'Original summary.', sort_order: 0 }),
          makeField('f2', 'Blockers', { content: 'Original blockers.', sort_order: 1 }),
        ],
      }),
    )

    let resolveF1: (field: ReportField) => void = () => {}
    let resolveF2: (field: ReportField) => void = () => {}
    vi.spyOn(reportsApi, 'updateFieldContent').mockImplementation((_reportId, fieldId) => {
      if (fieldId === 'f1') {
        return new Promise<ReportField>((resolve) => {
          resolveF1 = resolve
        })
      }
      return new Promise<ReportField>((resolve) => {
        resolveF2 = resolve
      })
    })

    renderDetailPage()
    await screen.findByRole('heading', { name: 'Kickoff' })

    // Scope each Save button to its own field's <li>, because field A's
    // button relabels to "Saving..." once its save is in flight -- an
    // unscoped `getAllByRole('button', { name: 'Save' })[1]` would then
    // silently point at the wrong element (or nothing).
    const [summaryContainer, blockersContainer] = screen
      .getAllByTestId('field-label')
      .map((label) => label.closest('li') as HTMLElement)

    // Start saving field A (Summary) first...
    await user.type(screen.getByLabelText('Summary content'), ' A-edit')
    await user.click(within(summaryContainer).getByRole('button', { name: 'Save' }))

    // ...then start saving field B (Blockers) before A's PATCH resolves.
    await user.type(screen.getByLabelText('Blockers content'), ' B-edit')
    await user.click(within(blockersContainer).getByRole('button', { name: 'Save' }))

    // B's save resolves first (out of order). Assert on the "Edited by you"
    // badge, which only appears once the server's is_user_edited field flows
    // through onSaved/setReport -- unlike the textarea's value, it cannot be
    // faked by what the user merely typed, so it is a true signal that B's
    // save was actually applied to report state.
    await act(async () => {
      resolveF2(
        makeField('f2', 'Blockers', {
          content: 'Original blockers. B-edit',
          sort_order: 1,
          is_user_edited: true,
        }),
      )
    })
    await waitFor(() => {
      expect(within(blockersContainer).getByText('Edited by you')).toBeInTheDocument()
    })

    // A's save resolves after. It must not revert B's already-applied edit.
    await act(async () => {
      resolveF1(
        makeField('f1', 'Summary', {
          content: 'Original summary. A-edit',
          sort_order: 0,
          is_user_edited: true,
        }),
      )
    })
    await waitFor(() => {
      expect(within(summaryContainer).getByText('Edited by you')).toBeInTheDocument()
    })

    // The lost-update bug would have reverted B to its pre-save state
    // (is_user_edited: false) when A's stale-closure save landed.
    expect(within(blockersContainer).getByText('Edited by you')).toBeInTheDocument()
    expect(screen.getByLabelText('Blockers content')).toHaveValue(
      'Original blockers. B-edit',
    )
  })

  it('appends a newly added field to the list', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({ fields: [makeField('f1', 'Summary', { sort_order: 0 })] }),
    )
    vi.spyOn(reportsApi, 'addField').mockResolvedValue(
      makeField('f2', 'Blockers', { sort_order: 1 }),
    )
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    await user.type(screen.getByLabelText('New field label'), 'Blockers')
    await user.click(screen.getByRole('button', { name: 'Add field' }))

    await waitFor(() => {
      expect(
        screen.getAllByTestId('field-label').map((node) => node.textContent),
      ).toEqual(['Summary', 'Blockers'])
    })
  })

  it('removes a deleted field from the list', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', { sort_order: 0 }),
          makeField('f2', 'Blockers', { sort_order: 1 }),
        ],
      }),
    )
    vi.spyOn(reportsApi, 'deleteField').mockResolvedValue(undefined)
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    await user.click(screen.getAllByRole('button', { name: 'Delete field' })[0])
    await user.click(screen.getByRole('button', { name: 'Delete field permanently' }))

    await waitFor(() => {
      expect(
        screen.getAllByTestId('field-label').map((node) => node.textContent),
      ).toEqual(['Blockers'])
    })
  })

  it('persists a reorder and shows the server order', async () => {
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', { sort_order: 0 }),
          makeField('f2', 'Blockers', { sort_order: 1 }),
        ],
      }),
    )
    const reorder = vi.spyOn(reportsApi, 'reorderFields').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f2', 'Blockers', { sort_order: 0 }),
          makeField('f1', 'Summary', { sort_order: 1 }),
        ],
      }),
    )
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    // The drag itself cannot run under jsdom, so the page's reorder callback is
    // exercised through the same path the drop would take.
    await act(async () => {
      window.dispatchEvent(
        new CustomEvent('test:reorder', { detail: ['f2', 'f1'] }),
      )
    })

    await waitFor(() => {
      expect(reorder).toHaveBeenCalledWith('r1', ['f2', 'f1'])
    })
    expect(
      screen.getAllByTestId('field-label').map((node) => node.textContent),
    ).toEqual(['Blockers', 'Summary'])
  })

  it('rolls the order back when the server rejects the reorder', async () => {
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', { sort_order: 0 }),
          makeField('f2', 'Blockers', { sort_order: 1 }),
        ],
      }),
    )
    vi.spyOn(reportsApi, 'reorderFields').mockRejectedValue(
      new ApiError(400, 'order mismatch'),
    )
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    await act(async () => {
      window.dispatchEvent(
        new CustomEvent('test:reorder', { detail: ['f2', 'f1'] }),
      )
    })

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That request was rejected. Check the file or the values you entered.',
    )
    expect(
      screen.getAllByTestId('field-label').map((node) => node.textContent),
    ).toEqual(['Summary', 'Blockers'])
  })

  it('replaces the whole report with the generated one', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'getReport').mockResolvedValue(
      makeReport({ fields: [makeField('f1', 'Summary', { sort_order: 0 })] }),
    )
    vi.spyOn(reportsApi, 'generateReport').mockResolvedValue(
      makeReport({
        fields: [
          makeField('f1', 'Summary', {
            content: 'The team shipped the parser.',
            sort_order: 0,
          }),
        ],
      }),
    )
    renderDetailPage()

    await screen.findByRole('heading', { name: 'Kickoff' })
    await user.click(screen.getByRole('button', { name: 'Generate content with AI' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Summary content')).toHaveValue(
        'The team shipped the parser.',
      )
    })
    expect(screen.getByText('AI draft')).toBeInTheDocument()
  })
})

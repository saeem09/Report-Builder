import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import * as reportsApi from '../../api/reports'
import { makeReport } from '../../test/fixtures'
import { ReportHeader } from './ReportHeader'

function renderHeader(onRenamed = vi.fn(), onDeleted = vi.fn()) {
  render(
    <ReportHeader
      report={makeReport({ name: 'Kickoff' })}
      onRenamed={onRenamed}
      onDeleted={onDeleted}
    />,
  )
  return { onRenamed, onDeleted }
}

describe('ReportHeader', () => {
  beforeEach(() => {
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: vi.fn(() => 'blob:fake'),
      revokeObjectURL: vi.fn(),
    })
    HTMLAnchorElement.prototype.click = vi.fn()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shows the report name as a heading', () => {
    renderHeader()

    expect(screen.getByRole('heading', { name: 'Kickoff' })).toBeInTheDocument()
  })

  it('renames the report and hands the updated report up', async () => {
    const user = userEvent.setup()
    const renamed = makeReport({ name: 'Kickoff v2' })
    const rename = vi.spyOn(reportsApi, 'renameReport').mockResolvedValue(renamed)
    const { onRenamed } = renderHeader()

    await user.click(screen.getByRole('button', { name: 'Rename' }))
    await user.clear(screen.getByLabelText('Report name'))
    await user.type(screen.getByLabelText('Report name'), 'Kickoff v2')
    await user.click(screen.getByRole('button', { name: 'Save name' }))

    await waitFor(() => {
      expect(rename).toHaveBeenCalledWith('r1', 'Kickoff v2')
    })
    expect(onRenamed).toHaveBeenCalledWith(renamed)
    expect(screen.queryByLabelText('Report name')).toBeNull()
  })

  it('abandons a rename on cancel without calling the api', async () => {
    const user = userEvent.setup()
    const rename = vi.spyOn(reportsApi, 'renameReport')
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Rename' }))
    await user.type(screen.getByLabelText('Report name'), ' edited')
    await user.click(screen.getByRole('button', { name: 'Cancel rename' }))

    expect(rename).not.toHaveBeenCalled()
    expect(screen.getByRole('heading', { name: 'Kickoff' })).toBeInTheDocument()
  })

  it('refuses to save a blank name', async () => {
    const user = userEvent.setup()
    const rename = vi.spyOn(reportsApi, 'renameReport')
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Rename' }))
    await user.clear(screen.getByLabelText('Report name'))

    expect(screen.getByRole('button', { name: 'Save name' })).toBeDisabled()
    expect(rename).not.toHaveBeenCalled()
  })

  it('surfaces a rename failure and keeps the editor open', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'renameReport').mockRejectedValue(new ApiError(404, 'gone'))
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Rename' }))
    await user.type(screen.getByLabelText('Report name'), '2')
    await user.click(screen.getByRole('button', { name: 'Save name' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That report or field no longer exists. Return to the reports list.',
    )
    expect(screen.getByLabelText('Report name')).toBeInTheDocument()
  })

  it('downloads the pdf with the filename the server supplies', async () => {
    const user = userEvent.setup()
    const exportPdf = vi.spyOn(reportsApi, 'exportReportPdf').mockResolvedValue({
      blob: new Blob(['%PDF-1.7']),
      contentDisposition: 'attachment; filename="Kickoff.pdf"',
    })
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Download PDF' }))

    await waitFor(() => {
      expect(exportPdf).toHaveBeenCalledWith('r1')
    })
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
  })

  it('shows an exporting state while the pdf is being built', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'exportReportPdf').mockReturnValue(new Promise(() => {}))
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Download PDF' }))

    expect(screen.getByRole('button', { name: 'Preparing PDF...' })).toBeDisabled()
  })

  it('surfaces a pdf export failure', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'exportReportPdf').mockRejectedValue(
      new ApiError(500, "The report's logo file is missing from storage."),
    )
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Download PDF' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The server could not complete that request. Try again.',
    )
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })

  it('asks for confirmation before deleting the report', async () => {
    const user = userEvent.setup()
    const remove = vi.spyOn(reportsApi, 'deleteReport')
    renderHeader()

    await user.click(screen.getByRole('button', { name: 'Delete report' }))

    expect(screen.getByRole('dialog')).toHaveAccessibleName('Delete this report')
    expect(remove).not.toHaveBeenCalled()
  })

  it('deletes the report when confirmed', async () => {
    const user = userEvent.setup()
    const remove = vi.spyOn(reportsApi, 'deleteReport').mockResolvedValue(undefined)
    const { onDeleted } = renderHeader()

    await user.click(screen.getByRole('button', { name: 'Delete report' }))
    await user.click(screen.getByRole('button', { name: 'Delete report permanently' }))

    await waitFor(() => {
      expect(remove).toHaveBeenCalledWith('r1')
    })
    expect(onDeleted).toHaveBeenCalledTimes(1)
  })

  it('does not delete when the confirmation is cancelled', async () => {
    const user = userEvent.setup()
    const remove = vi.spyOn(reportsApi, 'deleteReport')
    const { onDeleted } = renderHeader()

    await user.click(screen.getByRole('button', { name: 'Delete report' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(remove).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it('surfaces a delete failure without navigating away', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'deleteReport').mockRejectedValue(new ApiError(404, 'gone'))
    const { onDeleted } = renderHeader()

    await user.click(screen.getByRole('button', { name: 'Delete report' }))
    await user.click(screen.getByRole('button', { name: 'Delete report permanently' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That report or field no longer exists. Return to the reports list.',
    )
    expect(onDeleted).not.toHaveBeenCalled()
  })
})

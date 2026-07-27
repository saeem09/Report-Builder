import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import * as reportsApi from '../../api/reports'
import type { ReportDetail, SourceDocument } from '../../api/types'
import { makeReport } from '../../test/fixtures'
import { SourceDocumentPanel } from './SourceDocumentPanel'

function makeSource(id: string, name: string, sortOrder = 0): SourceDocument {
  return {
    id,
    report_id: 'r1',
    file_id: `file-${id}`,
    original_name: name,
    sort_order: sortOrder,
    created_at: '2026-07-27T10:00:00.000000Z',
  }
}

function renderPanel(onGenerated = vi.fn()) {
  render(<SourceDocumentPanel reportId="r1" onGenerated={onGenerated} />)
  return onGenerated
}

const NOTES = new File(['notes'], 'meeting-notes.txt', { type: 'text/plain' })
const MINUTES = new File(['minutes'], 'minutes.docx', {
  type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
})

describe('SourceDocumentPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the empty state before anything is uploaded', () => {
    renderPanel()

    expect(screen.getByText('No documents uploaded yet.')).toBeInTheDocument()
  })

  it('uploads a selected file and lists it by name', async () => {
    const user = userEvent.setup()
    const upload = vi
      .spyOn(reportsApi, 'uploadSourceDocument')
      .mockResolvedValue(makeSource('s1', 'meeting-notes.txt'))
    renderPanel()

    await user.upload(screen.getByLabelText('Add source documents'), NOTES)

    expect(await screen.findByText('meeting-notes.txt')).toBeInTheDocument()
    expect(upload).toHaveBeenCalledWith('r1', NOTES)
  })

  it('uploads several selected files one at a time, in order', async () => {
    const user = userEvent.setup()
    const upload = vi
      .spyOn(reportsApi, 'uploadSourceDocument')
      .mockResolvedValueOnce(makeSource('s1', 'meeting-notes.txt', 0))
      .mockResolvedValueOnce(makeSource('s2', 'minutes.docx', 1))
    renderPanel()

    await user.upload(screen.getByLabelText('Add source documents'), [NOTES, MINUTES])

    await waitFor(() => {
      expect(
        screen.getAllByTestId('source-name').map((node) => node.textContent),
      ).toEqual(['meeting-notes.txt', 'minutes.docx'])
    })
    expect(upload).toHaveBeenCalledTimes(2)
    expect(upload.mock.calls[0][1]).toBe(NOTES)
    expect(upload.mock.calls[1][1]).toBe(MINUTES)
  })

  it('shows the too-large message for a 413', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'uploadSourceDocument').mockRejectedValue(
      new ApiError(413, 'The uploaded file exceeds the 10485760 byte limit.'),
    )
    renderPanel()

    await user.upload(screen.getByLabelText('Add source documents'), NOTES)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That file is too large. The limit is 10 MB.',
    )
  })

  it('shows the rejected message for an unparseable file (400)', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'uploadSourceDocument').mockRejectedValue(
      new ApiError(400, 'Unsupported file type'),
    )
    renderPanel()

    await user.upload(screen.getByLabelText('Add source documents'), NOTES)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That request was rejected. Check the file or the values you entered.',
    )
  })

  it('keeps the successfully uploaded files when a later one fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'uploadSourceDocument')
      .mockResolvedValueOnce(makeSource('s1', 'meeting-notes.txt', 0))
      .mockRejectedValueOnce(new ApiError(400, 'Unsupported file type'))
    renderPanel()

    await user.upload(screen.getByLabelText('Add source documents'), [NOTES, MINUTES])

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('meeting-notes.txt')).toBeInTheDocument()
    expect(screen.queryByText('minutes.docx')).toBeNull()
  })

  it('shows a pending message while generation runs, then hands the report up', async () => {
    const user = userEvent.setup()
    const generated: ReportDetail = makeReport({ name: 'Kickoff' })
    let resolveGenerate: (report: ReportDetail) => void = () => {}
    vi.spyOn(reportsApi, 'generateReport').mockReturnValue(
      new Promise<ReportDetail>((resolve) => {
        resolveGenerate = resolve
      }),
    )
    const onGenerated = renderPanel()

    await user.click(screen.getByRole('button', { name: 'Generate content with AI' }))

    expect(
      screen.getByText(
        'Drafting content from your documents. This can take up to a minute.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generating...' })).toBeDisabled()

    resolveGenerate(generated)

    await waitFor(() => {
      expect(onGenerated).toHaveBeenCalledWith(generated)
    })
    expect(screen.getByRole('button', { name: 'Generate content with AI' })).toBeEnabled()
  })

  it('shows the no-documents message for a 409', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'generateReport').mockRejectedValue(
      new ApiError(409, 'This report has no source documents yet.'),
    )
    renderPanel()

    await user.click(screen.getByRole('button', { name: 'Generate content with AI' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Upload at least one source document before generating content.',
    )
  })

  it('shows the AI failure message for a 502', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'generateReport').mockRejectedValue(
      new ApiError(502, 'The AI service could not draft this report. Please try again.'),
    )
    const onGenerated = renderPanel()

    await user.click(screen.getByRole('button', { name: 'Generate content with AI' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The AI service could not draft this report. Please try again.',
    )
    expect(onGenerated).not.toHaveBeenCalled()
  })

  it('leaves the generate control enabled even with no documents in this session', () => {
    renderPanel()

    // The client cannot know the server's true source count, so it never
    // guesses. A report with no sources answers 409, which is rendered above.
    expect(screen.getByRole('button', { name: 'Generate content with AI' })).toBeEnabled()
  })
})

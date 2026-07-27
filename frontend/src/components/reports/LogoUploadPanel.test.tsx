import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import * as reportsApi from '../../api/reports'
import { makeReport } from '../../test/fixtures'
import { LogoUploadPanel } from './LogoUploadPanel'

const LOGO = new File(['png-bytes'], 'logo.png', { type: 'image/png' })

describe('LogoUploadPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('says no logo is set when logo_file_id is null', () => {
    render(<LogoUploadPanel report={makeReport()} onUploaded={vi.fn()} />)

    expect(screen.getByText('No logo uploaded yet.')).toBeInTheDocument()
  })

  it('says a logo is set when the report has one', () => {
    render(
      <LogoUploadPanel
        report={makeReport({ logo_file_id: 'file-1' })}
        onUploaded={vi.fn()}
      />,
    )

    expect(
      screen.getByText('A logo is set and will appear on the exported PDF.'),
    ).toBeInTheDocument()
  })

  it('uploads the chosen image and hands the updated report up', async () => {
    const user = userEvent.setup()
    const updated = makeReport({ logo_file_id: 'file-1' })
    const upload = vi.spyOn(reportsApi, 'uploadReportLogo').mockResolvedValue(updated)
    const onUploaded = vi.fn()
    render(<LogoUploadPanel report={makeReport()} onUploaded={onUploaded} />)

    await user.upload(screen.getByLabelText('Company logo image'), LOGO)

    await waitFor(() => {
      expect(upload).toHaveBeenCalledWith('r1', LOGO)
    })
    expect(onUploaded).toHaveBeenCalledWith(updated)
  })

  it('shows an uploading state while the request is in flight', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'uploadReportLogo').mockReturnValue(new Promise(() => {}))
    render(<LogoUploadPanel report={makeReport()} onUploaded={vi.fn()} />)

    await user.upload(screen.getByLabelText('Company logo image'), LOGO)

    expect(await screen.findByText('Uploading logo...')).toBeInTheDocument()
    expect(screen.getByLabelText('Company logo image')).toBeDisabled()
  })

  it('shows the rejected message when the server refuses the type (400)', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'uploadReportLogo').mockRejectedValue(
      new ApiError(400, 'The logo must be an image.'),
    )
    const onUploaded = vi.fn()
    render(<LogoUploadPanel report={makeReport()} onUploaded={onUploaded} />)

    await user.upload(screen.getByLabelText('Company logo image'), LOGO)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That request was rejected. Check the file or the values you entered.',
    )
    expect(onUploaded).not.toHaveBeenCalled()
  })

  it('shows the too-large message for a 413', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'uploadReportLogo').mockRejectedValue(
      new ApiError(413, 'too big'),
    )
    render(<LogoUploadPanel report={makeReport()} onUploaded={vi.fn()} />)

    await user.upload(screen.getByLabelText('Company logo image'), LOGO)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That file is too large. The limit is 10 MB.',
    )
  })

  it('restricts the picker to the image types the server accepts', () => {
    render(<LogoUploadPanel report={makeReport()} onUploaded={vi.fn()} />)

    expect(screen.getByLabelText('Company logo image')).toHaveAttribute(
      'accept',
      'image/png,image/jpeg,image/gif,image/webp',
    )
  })
})

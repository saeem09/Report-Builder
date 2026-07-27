import { afterEach, describe, expect, it, vi } from 'vitest'

import { filenameFromContentDisposition, triggerBlobDownload } from './download'

describe('filenameFromContentDisposition', () => {
  it('extracts a quoted filename', () => {
    expect(
      filenameFromContentDisposition('attachment; filename="Kickoff.pdf"', 'report.pdf'),
    ).toBe('Kickoff.pdf')
  })

  it('falls back when the header is absent', () => {
    expect(filenameFromContentDisposition(null, 'report.pdf')).toBe('report.pdf')
  })

  it('falls back when the header carries no filename', () => {
    expect(filenameFromContentDisposition('attachment', 'report.pdf')).toBe('report.pdf')
  })

  it('falls back when the filename is not quoted', () => {
    expect(
      filenameFromContentDisposition('attachment; filename=Kickoff.pdf', 'report.pdf'),
    ).toBe('report.pdf')
  })
})

describe('triggerBlobDownload', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('creates an object url, clicks a download anchor, then revokes and cleans up', () => {
    // jsdom implements neither createObjectURL nor anchor navigation, so both
    // are stubbed. Without the click stub, jsdom logs a "Not implemented:
    // navigation" error for every run.
    const createObjectURL = vi.fn(() => 'blob:fake')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })
    const clickedDownloads: string[] = []
    const originalClick = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function click(this: HTMLAnchorElement) {
      clickedDownloads.push(this.download)
    }

    try {
      triggerBlobDownload(new Blob(['%PDF-1.7']), 'Kickoff.pdf')
    } finally {
      HTMLAnchorElement.prototype.click = originalClick
    }

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(clickedDownloads).toEqual(['Kickoff.pdf'])
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:fake')
    expect(document.querySelectorAll('a')).toHaveLength(0)
  })
})

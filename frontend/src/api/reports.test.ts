import { afterEach, describe, expect, it, vi } from 'vitest'

import * as reportsApi from './reports'
import type { ReportDetail, ReportField, SourceDocument } from './types'

const FIELD: ReportField = {
  id: 'f1',
  report_id: 'r1',
  label: 'Summary',
  content: 'Drafted.',
  sort_order: 0,
  is_user_edited: false,
}

const REPORT: ReportDetail = {
  id: 'r1',
  name: 'Kickoff',
  logo_file_id: null,
  created_at: '2026-07-27T10:00:00.000000Z',
  updated_at: '2026-07-27T10:05:00.000000Z',
  fields: [FIELD],
}

const SOURCE: SourceDocument = {
  id: 's1',
  report_id: 'r1',
  file_id: 'file-1',
  original_name: 'notes.txt',
  sort_order: 0,
  created_at: '2026-07-27T10:01:00.000000Z',
}

function mockJson(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function lastCall(spy: ReturnType<typeof mockJson>): [string, RequestInit] {
  const call = spy.mock.calls[spy.mock.calls.length - 1]
  return [call[0] as string, (call[1] ?? {}) as RequestInit]
}

describe('reports api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('lists reports and unwraps the reports key', async () => {
    const spy = mockJson({ reports: [{ ...REPORT, fields: undefined }] })

    const result = await reportsApi.listReports()

    expect(lastCall(spy)[0]).toBe('http://localhost:8000/api/reports')
    expect(result).toHaveLength(1)
  })

  it('creates a report with its initial field labels', async () => {
    const spy = mockJson(REPORT, 201)

    await reportsApi.createReport('Kickoff', ['Summary', 'Blockers'])

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({
      name: 'Kickoff',
      field_labels: ['Summary', 'Blockers'],
    })
  })

  it('gets one report', async () => {
    const spy = mockJson(REPORT)

    await reportsApi.getReport('r1')

    expect(lastCall(spy)[0]).toBe('http://localhost:8000/api/reports/r1')
  })

  it('url-encodes an id that contains a slash', async () => {
    const spy = mockJson(REPORT)

    await reportsApi.getReport('a/b')

    expect(lastCall(spy)[0]).toBe('http://localhost:8000/api/reports/a%2Fb')
  })

  it('renames a report with PATCH', async () => {
    const spy = mockJson(REPORT)

    await reportsApi.renameReport('r1', 'Kickoff v2')

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ name: 'Kickoff v2' })
  })

  it('deletes a report with DELETE', async () => {
    const spy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }))

    await reportsApi.deleteReport('r1')

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1')
    expect(init.method).toBe('DELETE')
  })

  it('adds a field with POST', async () => {
    const spy = mockJson(FIELD, 201)

    await reportsApi.addField('r1', 'Blockers')

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/fields')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ label: 'Blockers' })
  })

  it('sends the complete ordered id list to the order endpoint', async () => {
    const spy = mockJson(REPORT)

    await reportsApi.reorderFields('r1', ['f2', 'f1'])

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/fields/order')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body as string)).toEqual({ field_ids: ['f2', 'f1'] })
  })

  it('updates field content with PATCH', async () => {
    const spy = mockJson(FIELD)

    await reportsApi.updateFieldContent('r1', 'f1', 'Hand written.')

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/fields/f1')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ content: 'Hand written.' })
  })

  it('deletes a field with DELETE', async () => {
    const spy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 204 }))

    await reportsApi.deleteField('r1', 'f1')

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/fields/f1')
    expect(init.method).toBe('DELETE')
  })

  it('uploads a source document as multipart form data', async () => {
    const spy = mockJson(SOURCE, 201)
    const file = new File(['notes'], 'notes.txt', { type: 'text/plain' })

    await reportsApi.uploadSourceDocument('r1', file)

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/documents')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).get('file')).toBe(file)
  })

  it('does not set a content type on a multipart request', async () => {
    const spy = mockJson(SOURCE, 201)

    await reportsApi.uploadSourceDocument(
      'r1',
      new File(['notes'], 'notes.txt', { type: 'text/plain' }),
    )

    expect(lastCall(spy)[1].headers).toBeUndefined()
  })

  it('triggers generation with POST and no body', async () => {
    const spy = mockJson(REPORT)

    await reportsApi.generateReport('r1')

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/generate')
    expect(init.method).toBe('POST')
    expect(init.body).toBeUndefined()
  })

  it('uploads a logo with PUT and multipart form data', async () => {
    const spy = mockJson(REPORT)
    const file = new File(['png'], 'logo.png', { type: 'image/png' })

    await reportsApi.uploadReportLogo('r1', file)

    const [url, init] = lastCall(spy)
    expect(url).toBe('http://localhost:8000/api/reports/r1/logo')
    expect(init.method).toBe('PUT')
    expect((init.body as FormData).get('file')).toBe(file)
  })

  it('exports the pdf and returns the blob with its filename header', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('%PDF-1.7', {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="Kickoff.pdf"',
        },
      }),
    )

    const result = await reportsApi.exportReportPdf('r1')

    expect(lastCall(spy)[0]).toBe('http://localhost:8000/api/reports/r1/export.pdf')
    expect(result.contentDisposition).toBe('attachment; filename="Kickoff.pdf"')
  })
})

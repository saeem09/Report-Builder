import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, NetworkError, requestBlob, requestJson, requestVoid } from './client'

function mockFetch(response: Response) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(response)
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('prefixes the base url and parses the json body', async () => {
    const fetchSpy = mockFetch(jsonResponse({ reports: [] }))

    const result = await requestJson<{ reports: unknown[] }>('/api/reports')

    expect(fetchSpy).toHaveBeenCalledWith('http://localhost:8000/api/reports', {})
    expect(result).toEqual({ reports: [] })
  })

  it('passes the supplied init through to fetch', async () => {
    const fetchSpy = mockFetch(jsonResponse({ id: 'r1' }, 201))

    await requestJson('/api/reports', { method: 'POST', body: '{}' })

    expect(fetchSpy).toHaveBeenCalledWith('http://localhost:8000/api/reports', {
      method: 'POST',
      body: '{}',
    })
  })

  it('throws an ApiError carrying the status and the string detail', async () => {
    mockFetch(jsonResponse({ detail: 'No report exists with id.' }, 404))

    await expect(requestJson('/api/reports/x')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'No report exists with id.',
    })
  })

  it('joins a pydantic 422 detail list into one message', async () => {
    mockFetch(
      jsonResponse(
        {
          detail: [
            { loc: ['body', 'name'], msg: 'Value error, must not be blank' },
            { loc: ['body', 'name'], msg: 'String too short' },
          ],
        },
        422,
      ),
    )

    await expect(requestJson('/api/reports')).rejects.toThrow(
      'Value error, must not be blank; String too short',
    )
  })

  it('falls back to a status message when the error body is not json', async () => {
    mockFetch(new Response('boom', { status: 500 }))

    await expect(requestJson('/api/reports')).rejects.toThrow(
      'Request failed with status 500.',
    )
  })

  it('falls back to a status message when detail is an unexpected shape', async () => {
    mockFetch(jsonResponse({ detail: { unexpected: true } }, 400))

    await expect(requestJson('/api/reports')).rejects.toThrow(
      'Request failed with status 400.',
    )
  })

  it('throws a NetworkError when fetch itself rejects', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(requestJson('/api/reports')).rejects.toBeInstanceOf(NetworkError)
  })

  it('resolves to undefined for a 204 response', async () => {
    mockFetch(new Response(null, { status: 204 }))

    await expect(
      requestVoid('/api/reports/x', { method: 'DELETE' }),
    ).resolves.toBeUndefined()
  })

  it('throws an ApiError from requestVoid for a failure status', async () => {
    mockFetch(jsonResponse({ detail: 'gone' }, 404))

    await expect(requestVoid('/api/reports/x', { method: 'DELETE' })).rejects.toMatchObject(
      { status: 404 },
    )
  })

  it('returns the blob and the content disposition header', async () => {
    mockFetch(
      new Response('%PDF-1.7', {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="Kickoff.pdf"',
        },
      }),
    )

    const result = await requestBlob('/api/reports/x/export.pdf')

    expect(result.contentDisposition).toBe('attachment; filename="Kickoff.pdf"')
    expect(await result.blob.text()).toBe('%PDF-1.7')
  })

  it('returns a null content disposition when the header is absent', async () => {
    mockFetch(new Response('%PDF-1.7', { status: 200 }))

    const result = await requestBlob('/api/reports/x/export.pdf')

    expect(result.contentDisposition).toBeNull()
  })

  it('exposes ApiError and NetworkError as Error subclasses', () => {
    expect(new ApiError(409, 'x')).toBeInstanceOf(Error)
    expect(new NetworkError('x')).toBeInstanceOf(Error)
  })
})

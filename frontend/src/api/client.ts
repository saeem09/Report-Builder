/**
 * The one place this application talks to the network.
 *
 * Every non-2xx response becomes an ApiError carrying the status code, and
 * every transport failure becomes a NetworkError, so no caller ever has to
 * inspect a Response object or guess whether a rejection means "the server
 * said no" or "the server was not there".
 */

const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE_URL

/** The server answered with a non-2xx status. status is the HTTP code. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** fetch itself rejected: the backend is down, or DNS or CORS refused it. */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NetworkError'
  }
}

type DetailItem = { msg?: unknown }

/**
 * FastAPI sends detail as a string for domain errors and as a list of
 * {loc, msg, type} objects for 422 request-validation failures. Both are
 * flattened to one string here so callers see one error shape.
 */
function detailToMessage(detail: unknown): string | null {
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = (detail as DetailItem[])
      .map((item) => (typeof item.msg === 'string' ? item.msg : null))
      .filter((message): message is string => message !== null)
    return messages.length > 0 ? messages.join('; ') : null
  }
  return null
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body !== null && typeof body === 'object' && 'detail' in body) {
      const message = detailToMessage((body as { detail: unknown }).detail)
      if (message !== null) {
        return message
      }
    }
  } catch {
    // A non-JSON error body is possible (a proxy page, an empty body). Fall
    // through to the status message rather than masking the real status with
    // a parse error.
  }
  return `Request failed with status ${response.status}.`
}

async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    throw new NetworkError(
      'Could not reach the server. Check that the backend is running.',
    )
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response))
  }
  return response
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await send(path, init)
  return (await response.json()) as T
}

/** For 204 endpoints. The body is never read. */
export async function requestVoid(path: string, init: RequestInit = {}): Promise<void> {
  await send(path, init)
}

export async function requestBlob(
  path: string,
  init: RequestInit = {},
): Promise<{ blob: Blob; contentDisposition: string | null }> {
  const response = await send(path, init)
  return {
    blob: await response.blob(),
    contentDisposition: response.headers.get('Content-Disposition'),
  }
}

/**
 * Build the headers and body for a JSON request. Spread into a RequestInit
 * alongside the method so the method is always visible at the call site.
 */
export function jsonBody(payload: unknown): RequestInit {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }
}

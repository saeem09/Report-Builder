/**
 * Turning a fetched Blob into a file the browser saves.
 *
 * The PDF is fetched rather than linked with a plain anchor so a 404 or a 500
 * becomes an error banner in the app instead of FastAPI's JSON error page in a
 * new tab. That matters because the export really can fail: a report whose
 * logo file is missing from storage answers 500.
 */

// Deliberately only the quoted form. The server always sends filename="..."
// with a slug restricted to [A-Za-z0-9._-], so there is nothing else to parse
// and no reason to accept a shape the server never produces.
const FILENAME_PATTERN = /filename="([^"]+)"/

export function filenameFromContentDisposition(
  header: string | null,
  fallback: string,
): string {
  if (header === null) {
    return fallback
  }
  const match = FILENAME_PATTERN.exec(header)
  return match === null ? fallback : match[1]
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  anchor.rel = 'noopener'
  // The anchor must be in the document for the click to be honoured in some
  // browsers, and it is removed immediately afterwards so nothing accumulates.
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(objectUrl)
}

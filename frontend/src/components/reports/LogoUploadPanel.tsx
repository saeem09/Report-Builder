import { useRef, useState } from 'react'

import { uploadReportLogo } from '../../api/reports'
import type { ReportDetail } from '../../api/types'
import { ErrorBanner } from '../ui/ErrorBanner'

// Mirrors ALLOWED_LOGO_CONTENT_TYPES in backend/app/reports/pipeline_routes.py.
// This only filters the file picker; the server is what actually enforces it,
// and a rejected type comes back as a 400 rendered by the banner below.
const ACCEPTED_IMAGE_TYPES = 'image/png,image/jpeg,image/gif,image/webp'

type LogoUploadPanelProps = {
  report: ReportDetail
  onUploaded: (report: ReportDetail) => void
}

/**
 * Uploading again simply replaces the current logo, which is why the endpoint
 * is a PUT and why there is no separate "remove" control: a report either has
 * the logo you last uploaded or none at all.
 */
export function LogoUploadPanel({ report, onUploaded }: LogoUploadPanelProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFileSelected(files: FileList | null) {
    const file = files?.[0]
    if (file === undefined) {
      return
    }
    setIsUploading(true)
    setError(null)
    try {
      onUploaded(await uploadReportLogo(report.id, file))
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsUploading(false)
      // Reset so re-selecting the same file still fires a change event.
      if (inputRef.current !== null) {
        inputRef.current.value = ''
      }
    }
  }

  return (
    <section className="rounded-md border border-grey-light bg-white p-4">
      <h3 className="text-lg font-semibold text-navy-deep">Company logo</h3>
      <p className="mt-1 text-sm text-grey-mid">
        {report.logo_file_id === null
          ? 'No logo uploaded yet.'
          : 'A logo is set and will appear on the exported PDF.'}
      </p>

      <label
        htmlFor="report-logo-input"
        className="mt-3 block text-sm font-medium text-charcoal"
      >
        Company logo image
      </label>
      <input
        id="report-logo-input"
        ref={inputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES}
        disabled={isUploading}
        onChange={(event) => void handleFileSelected(event.target.files)}
        className="mt-1 block w-full text-sm text-charcoal file:mr-3 file:rounded-md file:border file:border-blue-steel file:bg-white file:px-3 file:py-1 file:text-navy-deep"
      />

      {isUploading ? (
        <p role="status" className="mt-2 text-sm text-grey-mid">
          Uploading logo...
        </p>
      ) : null}

      <div className="mt-3">
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
      </div>
    </section>
  )
}

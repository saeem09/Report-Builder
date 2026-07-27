import { useState } from 'react'

import { deleteReport, exportReportPdf, renameReport } from '../../api/reports'
import type { ReportDetail } from '../../api/types'
import { filenameFromContentDisposition, triggerBlobDownload } from '../../lib/download'
import { Button } from '../ui/Button'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { ErrorBanner } from '../ui/ErrorBanner'
import { TextInput } from '../ui/TextInput'

// Mirrors MAX_NAME_LENGTH in backend/app/reports/schemas.py.
const MAX_NAME_LENGTH = 200
const FALLBACK_PDF_FILENAME = 'report.pdf'

function formatTimestamp(isoTimestamp: string): string {
  const parsed = new Date(isoTimestamp)
  return Number.isNaN(parsed.getTime()) ? isoTimestamp : parsed.toLocaleString()
}

type ReportHeaderProps = {
  report: ReportDetail
  onRenamed: (report: ReportDetail) => void
  onDeleted: () => void
}

/**
 * The report's identity and its three report-level actions.
 *
 * Rename is an inline editor rather than a dialog because it is not
 * destructive and the user is already looking at the value. Delete is a
 * dialog because it removes the report, its fields, and its sources for good.
 */
export function ReportHeader({ report, onRenamed, onDeleted }: ReportHeaderProps) {
  const [isRenaming, setIsRenaming] = useState(false)
  const [draftName, setDraftName] = useState(report.name)
  const [isSavingName, setIsSavingName] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const trimmedName = draftName.trim()
  const canSaveName = trimmedName.length > 0 && !isSavingName

  function startRenaming() {
    setDraftName(report.name)
    setError(null)
    setIsRenaming(true)
  }

  async function handleSaveName() {
    if (!canSaveName) {
      return
    }
    setIsSavingName(true)
    setError(null)
    try {
      onRenamed(await renameReport(report.id, trimmedName))
      setIsRenaming(false)
    } catch (caught: unknown) {
      // The editor stays open so the typed name is not lost.
      setError(caught)
    } finally {
      setIsSavingName(false)
    }
  }

  async function handleExport() {
    setIsExporting(true)
    setError(null)
    try {
      const { blob, contentDisposition } = await exportReportPdf(report.id)
      triggerBlobDownload(
        blob,
        filenameFromContentDisposition(contentDisposition, FALLBACK_PDF_FILENAME),
      )
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsExporting(false)
    }
  }

  async function handleConfirmDelete() {
    setIsConfirmingDelete(false)
    setIsDeleting(true)
    setError(null)
    try {
      await deleteReport(report.id)
      onDeleted()
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {isRenaming ? (
        <div className="max-w-md">
          <TextInput
            id="report-name"
            label="Report name"
            value={draftName}
            onChange={setDraftName}
            maxLength={MAX_NAME_LENGTH}
          />
          <div className="mt-3 flex gap-3">
            <Button onClick={() => void handleSaveName()} disabled={!canSaveName}>
              {isSavingName ? 'Saving...' : 'Save name'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setIsRenaming(false)}
              disabled={isSavingName}
            >
              Cancel rename
            </Button>
          </div>
        </div>
      ) : (
        <div>
          <h2 className="text-xl font-semibold text-navy-deep">{report.name}</h2>
          <p className="text-sm text-grey-mid">
            Updated {formatTimestamp(report.updated_at)}
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        {isRenaming ? null : (
          <Button variant="secondary" onClick={startRenaming}>
            Rename
          </Button>
        )}
        <Button onClick={() => void handleExport()} disabled={isExporting}>
          {isExporting ? 'Preparing PDF...' : 'Download PDF'}
        </Button>
        <Button
          variant="danger"
          onClick={() => setIsConfirmingDelete(true)}
          disabled={isDeleting}
        >
          {isDeleting ? 'Deleting...' : 'Delete report'}
        </Button>
      </div>

      <ErrorBanner error={error} onDismiss={() => setError(null)} />

      {isConfirmingDelete ? (
        <ConfirmDialog
          title="Delete this report"
          message={`"${report.name}", all of its fields, and all of its uploaded source documents will be removed. This cannot be undone.`}
          confirmLabel="Delete report permanently"
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setIsConfirmingDelete(false)}
        />
      ) : null}
    </div>
  )
}

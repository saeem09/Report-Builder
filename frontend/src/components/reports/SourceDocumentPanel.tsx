import { useRef, useState } from 'react'

import { generateReport, uploadSourceDocument } from '../../api/reports'
import type { ReportDetail, SourceDocument } from '../../api/types'
import { Button } from '../ui/Button'
import { ErrorBanner } from '../ui/ErrorBanner'

// Matches the formats backend/app/parsers supports.
const ACCEPTED_TYPES = '.docx,.pdf,.html,.htm,.txt'

type SourceDocumentPanelProps = {
  reportId: string
  onGenerated: (report: ReportDetail) => void
}

/**
 * Upload the meeting material a report is drafted from, and trigger the one
 * batched AI call that drafts it.
 *
 * The document list here covers only this visit: the API has no endpoint that
 * reads a report's existing sources, so there is nothing to load on mount. The
 * copy says so rather than implying the list is complete. For the same reason
 * the generate control is never disabled on a client-side count - the server
 * answers 409 when there is genuinely nothing to draft from, and that is the
 * only trustworthy source of that fact.
 */
export function SourceDocumentPanel({
  reportId,
  onGenerated,
}: SourceDocumentPanelProps) {
  const [documents, setDocuments] = useState<readonly SourceDocument[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFilesSelected(files: FileList | null) {
    if (files === null || files.length === 0) {
      return
    }
    setIsUploading(true)
    setError(null)
    try {
      // Sequential, not Promise.all: the server derives sort_order from
      // MAX(sort_order) + 1 per request, so concurrent uploads would race for
      // the same position. Sequential upload also means a failure part-way
      // leaves every earlier file recorded and listed.
      for (const file of Array.from(files)) {
        const uploaded = await uploadSourceDocument(reportId, file)
        setDocuments((current) => [...current, uploaded])
      }
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsUploading(false)
      // Reset the control so selecting the same file again still fires change.
      if (inputRef.current !== null) {
        inputRef.current.value = ''
      }
    }
  }

  async function handleGenerate() {
    setIsGenerating(true)
    setError(null)
    try {
      onGenerated(await generateReport(reportId))
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <section className="rounded-md border border-grey-light bg-white p-4">
      <h3 className="text-lg font-semibold text-navy-deep">Source documents</h3>
      <p className="mt-1 text-sm text-grey-mid">
        Word, PDF, HTML, or plain text, up to 10 MB each. Documents uploaded in this
        session are listed below. Every document attached to this report is used when
        content is generated.
      </p>

      <label
        htmlFor="source-document-input"
        className="mt-3 block text-sm font-medium text-charcoal"
      >
        Add source documents
      </label>
      <input
        id="source-document-input"
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_TYPES}
        disabled={isUploading}
        onChange={(event) => void handleFilesSelected(event.target.files)}
        className="mt-1 block w-full text-sm text-charcoal file:mr-3 file:rounded-md file:border file:border-blue-steel file:bg-white file:px-3 file:py-1 file:text-navy-deep"
      />

      {isUploading ? (
        <p role="status" className="mt-2 text-sm text-grey-mid">
          Uploading...
        </p>
      ) : null}

      {documents.length === 0 ? (
        <p className="mt-3 text-sm text-grey-mid">No documents uploaded yet.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-1">
          {documents.map((document_) => (
            <li
              key={document_.id}
              data-testid="source-name"
              className="text-sm text-charcoal"
            >
              {document_.original_name}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4">
        <Button onClick={() => void handleGenerate()} disabled={isGenerating}>
          {isGenerating ? 'Generating...' : 'Generate content with AI'}
        </Button>
      </div>

      {isGenerating ? (
        <p role="status" className="mt-2 text-sm text-grey-mid">
          Drafting content from your documents. This can take up to a minute.
        </p>
      ) : null}

      <p className="mt-2 text-sm text-grey-mid">
        Fields you have edited yourself are never overwritten.
      </p>

      <div className="mt-3">
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
      </div>
    </section>
  )
}

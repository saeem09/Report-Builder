import { useState } from 'react'

import { createReport } from '../../api/reports'
import type { ReportDetail } from '../../api/types'
import { Button } from '../ui/Button'
import { ErrorBanner } from '../ui/ErrorBanner'
import { TextArea } from '../ui/TextArea'
import { TextInput } from '../ui/TextInput'

// Mirrors MAX_NAME_LENGTH and MAX_LABEL_LENGTH in backend/app/reports/schemas.py.
const MAX_NAME_LENGTH = 200
const BLANK_NAME_MESSAGE = 'Enter a name for this report.'

/**
 * Labels are entered one per line. The server rejects a blank label with 422,
 * so blank lines are dropped here rather than turned into a failed request.
 */
function parseLabels(raw: string): string[] {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}

type CreateReportFormProps = {
  onCreated: (report: ReportDetail) => void
}

export function CreateReportForm({ onCreated }: CreateReportFormProps) {
  const [name, setName] = useState('')
  const [labelsText, setLabelsText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (trimmedName.length === 0) {
      setError(new Error(BLANK_NAME_MESSAGE))
      return
    }
    setIsSubmitting(true)
    setError(null)
    try {
      onCreated(await createReport(trimmedName, parseLabels(labelsText)))
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsSubmitting(false)
    }
  }

  // A local validation failure is a plain Error, which toUserMessage would turn
  // into its generic fallback. Rendering the message directly keeps the
  // specific guidance while every server error still goes through ErrorBanner.
  const isLocalValidationError =
    error instanceof Error && error.message === BLANK_NAME_MESSAGE

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="flex flex-col gap-4">
      <TextInput
        id="report-name"
        label="Report name"
        value={name}
        onChange={setName}
        maxLength={MAX_NAME_LENGTH}
        placeholder="Sprint 4 progress"
      />

      <TextArea
        id="report-field-labels"
        label="Initial field labels (one per line, optional)"
        value={labelsText}
        onChange={setLabelsText}
        rows={5}
        placeholder={'Summary\nBlockers\nNext steps'}
      />

      {isLocalValidationError ? (
        <div
          role="alert"
          className="rounded-md border border-navy-dark bg-tint-sky-alt px-4 py-3 text-charcoal"
        >
          <p>{BLANK_NAME_MESSAGE}</p>
        </div>
      ) : (
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
      )}

      <div>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating...' : 'Create report'}
        </Button>
      </div>
    </form>
  )
}

import { useState } from 'react'

import { addField } from '../../api/reports'
import type { ReportField } from '../../api/types'
import { Button } from '../ui/Button'
import { ErrorBanner } from '../ui/ErrorBanner'
import { TextInput } from '../ui/TextInput'

// Mirrors MAX_LABEL_LENGTH in backend/app/reports/schemas.py.
const MAX_LABEL_LENGTH = 200

type AddFieldFormProps = {
  reportId: string
  onAdded: (field: ReportField) => void
}

export function AddFieldForm({ reportId, onAdded }: AddFieldFormProps) {
  const [label, setLabel] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const trimmedLabel = label.trim()
  const canSubmit = trimmedLabel.length > 0 && !isSubmitting

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }
    setIsSubmitting(true)
    setError(null)
    try {
      onAdded(await addField(reportId, trimmedLabel))
      // Cleared only on success, so a failed add does not lose what was typed.
      setLabel('')
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={(event) => void handleSubmit(event)}
      className="rounded-md border border-grey-light bg-white p-4"
    >
      <TextInput
        id="new-field-label"
        label="New field label"
        value={label}
        onChange={setLabel}
        maxLength={MAX_LABEL_LENGTH}
        placeholder="Next steps"
      />
      <div className="mt-3">
        <Button type="submit" disabled={!canSubmit}>
          {isSubmitting ? 'Adding...' : 'Add field'}
        </Button>
      </div>
      <div className="mt-3">
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
      </div>
    </form>
  )
}

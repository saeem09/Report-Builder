import { useEffect, useState } from 'react'

import { updateFieldContent } from '../../api/reports'
import type { ReportField } from '../../api/types'
import { Button } from '../ui/Button'
import { ErrorBanner } from '../ui/ErrorBanner'
import { TextArea } from '../ui/TextArea'

// Mirrors MAX_CONTENT_LENGTH in backend/app/reports/schemas.py.
const MAX_CONTENT_LENGTH = 50000

const BADGE_CLASSES = 'rounded-md px-2 py-1 text-xs font-semibold'

/**
 * Provenance is shown as words, not colour alone, so it does not depend on
 * colour perception. An empty untouched field gets no badge because it has no
 * provenance yet.
 */
function ProvenanceBadge({ field }: { field: ReportField }) {
  if (field.is_user_edited) {
    return (
      <span className={`${BADGE_CLASSES} bg-tint-sky text-navy-dark`}>
        Edited by you
      </span>
    )
  }
  if (field.content.length > 0) {
    return (
      <span className={`${BADGE_CLASSES} bg-grey-pale text-grey-mid`}>AI draft</span>
    )
  }
  return null
}

type ReportFieldCardProps = {
  reportId: string
  field: ReportField
  onSaved: (field: ReportField) => void
}

/**
 * Content is saved on an explicit click, never on a timer.
 *
 * PATCH /api/reports/{id}/fields/{field_id} sets is_user_edited permanently,
 * and Phase 4a's generation step then skips that field on every future run. A
 * debounced autosave would fire that irreversible flag on a stray keystroke
 * and quietly remove the field from AI drafting forever. The Save button is
 * what makes taking ownership of a field a decision rather than an accident.
 */
export function ReportFieldCard({ reportId, field, onSaved }: ReportFieldCardProps) {
  const [draft, setDraft] = useState(field.content)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<unknown>(null)

  // Re-sync when the server replaces this field's content, which happens after
  // an AI generation run. Keyed on the saved content, so it never clobbers a
  // draft the user is still typing unless the underlying field really changed.
  useEffect(() => {
    setDraft(field.content)
  }, [field.content])

  const isDirty = draft !== field.content
  const contentInputId = `field-content-${field.id}`

  async function handleSave() {
    setIsSaving(true)
    setError(null)
    try {
      onSaved(await updateFieldContent(reportId, field.id, draft))
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex-1 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 data-testid="field-label" className="font-semibold text-navy-deep">
          {field.label}
        </h3>
        <ProvenanceBadge field={field} />
      </div>

      <TextArea
        id={contentInputId}
        label={`${field.label} content`}
        value={draft}
        onChange={setDraft}
        maxLength={MAX_CONTENT_LENGTH}
      />

      <div className="mt-3 flex items-center gap-3">
        <Button onClick={() => void handleSave()} disabled={!isDirty || isSaving}>
          {isSaving ? 'Saving...' : 'Save'}
        </Button>
        <Button
          variant="secondary"
          onClick={() => setDraft(field.content)}
          disabled={!isDirty || isSaving}
        >
          Revert
        </Button>
        {isDirty ? (
          <span className="text-sm text-grey-mid">Unsaved changes</span>
        ) : null}
      </div>

      <div className="mt-3">
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
      </div>
    </div>
  )
}

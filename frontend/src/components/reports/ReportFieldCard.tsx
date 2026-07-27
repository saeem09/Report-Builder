import { useEffect, useRef, useState } from 'react'

import { deleteField, updateFieldContent } from '../../api/reports'
import type { ReportField } from '../../api/types'
import { Button } from '../ui/Button'
import { ConfirmDialog } from '../ui/ConfirmDialog'
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
  onDeleted: (fieldId: string) => void
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
export function ReportFieldCard({
  reportId,
  field,
  onSaved,
  onDeleted,
}: ReportFieldCardProps) {
  const [draft, setDraft] = useState(field.content)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false)
  const [error, setError] = useState<unknown>(null)

  // Re-sync when the server replaces this field's content, which happens after
  // an AI generation run or this card's own save. lastSyncedContent tracks
  // what draft was set to last time, so this only adopts the new value when
  // the user hasn't typed anything since — an unrelated mutation (e.g.
  // generation resolving while the user is mid-edit on this field) must never
  // silently overwrite unsaved keystrokes. draftRef mirrors draft so the
  // effect can read its latest value without depending on it, since a
  // dependency on draft itself would make this fire on every keystroke.
  const draftRef = useRef(draft)
  draftRef.current = draft
  const lastSyncedContent = useRef(field.content)
  useEffect(() => {
    if (draftRef.current === lastSyncedContent.current) {
      setDraft(field.content)
    }
    lastSyncedContent.current = field.content
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

  async function handleConfirmDelete() {
    // The dialog closes first so the error banner, if any, is not hidden
    // behind the overlay.
    setIsConfirmingDelete(false)
    setIsDeleting(true)
    setError(null)
    try {
      await deleteField(reportId, field.id)
      onDeleted(field.id)
    } catch (caught: unknown) {
      setError(caught)
    } finally {
      setIsDeleting(false)
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

      <div className="mt-3 flex flex-wrap items-center gap-3">
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
        <Button
          variant="danger"
          onClick={() => setIsConfirmingDelete(true)}
          disabled={isDeleting}
        >
          {isDeleting ? 'Deleting...' : 'Delete field'}
        </Button>
        {isDirty ? (
          <span className="text-sm text-grey-mid">Unsaved changes</span>
        ) : null}
      </div>

      <div className="mt-3">
        <ErrorBanner error={error} onDismiss={() => setError(null)} />
      </div>

      {isConfirmingDelete ? (
        <ConfirmDialog
          title="Delete this field"
          message={`"${field.label}" and its content will be removed from this report. This cannot be undone.`}
          confirmLabel="Delete field permanently"
          onConfirm={() => void handleConfirmDelete()}
          onCancel={() => setIsConfirmingDelete(false)}
        />
      ) : null}
    </div>
  )
}

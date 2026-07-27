import { useEffect, useRef } from 'react'

type ConfirmDialogProps = {
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}

/**
 * A plain overlay rather than the native <dialog> element: showModal's jsdom
 * support is uneven, and this needs no top-layer behaviour that a fixed
 * overlay does not already give. Cancel takes focus on mount so the safe
 * option is what Enter and Escape both reach first.
 */
export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onCancel()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        className="w-full max-w-md rounded-md border border-grey-light bg-white p-6"
      >
        <h2 id="confirm-dialog-title" className="text-lg font-semibold text-navy-deep">
          {title}
        </h2>
        <p className="mt-2 text-charcoal">{message}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="inline-flex items-center rounded-md border border-blue-steel bg-white px-4 py-2 text-sm font-semibold text-navy-deep hover:bg-tint-sky"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="inline-flex items-center rounded-md bg-navy-dark px-4 py-2 text-sm font-semibold text-white hover:bg-charcoal"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

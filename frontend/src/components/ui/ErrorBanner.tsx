import { ApiError, NetworkError } from '../../api/client'

/**
 * One status code, one sentence. The server's own detail strings are accurate
 * but written for a developer; these are written for the person using the app
 * and tell them what to do next.
 */
const STATUS_MESSAGES: Record<number, string> = {
  400: 'That request was rejected. Check the file or the values you entered.',
  404: 'That report or field no longer exists. Return to the reports list.',
  409: 'Upload at least one source document before generating content.',
  413: 'That file is too large. The limit is 10 MB.',
  422: 'Some values are not valid. Check the highlighted fields.',
  500: 'The server could not complete that request. Try again.',
  502: 'The AI service could not draft this report. Please try again.',
}

const FALLBACK_MESSAGE = 'Something went wrong. Please try again.'

export function toUserMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return STATUS_MESSAGES[error.status] ?? error.message
  }
  if (error instanceof NetworkError) {
    return error.message
  }
  // An unexpected throwable is a bug, not a message for the user. Its text
  // could be a stack detail or an internal name, so it is never rendered.
  return FALLBACK_MESSAGE
}

type ErrorBannerProps = {
  error: unknown
  onDismiss?: () => void
}

export function ErrorBanner({ error, onDismiss }: ErrorBannerProps) {
  if (error === null || error === undefined) {
    return null
  }
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-4 rounded-md border border-navy-dark bg-tint-sky-alt px-4 py-3 text-charcoal"
    >
      <p>{toUserMessage(error)}</p>
      {onDismiss !== undefined ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="shrink-0 text-sm font-semibold text-grey-mid hover:text-navy-deep"
        >
          Dismiss
        </button>
      ) : null}
    </div>
  )
}

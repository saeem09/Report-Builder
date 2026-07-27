import { useCallback, useEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import { Link, useParams } from 'react-router-dom'

import { getReport, reorderFields } from '../api/reports'
import type { ReportDetail } from '../api/types'
import { AddFieldForm } from '../components/reports/AddFieldForm'
import { LogoUploadPanel } from '../components/reports/LogoUploadPanel'
import { ReportFieldCard } from '../components/reports/ReportFieldCard'
import { SortableFieldList } from '../components/reports/SortableFieldList'
import { SourceDocumentPanel } from '../components/reports/SourceDocumentPanel'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { appendField, removeField, replaceField, withFieldOrder } from '../lib/reportState'

function formatTimestamp(isoTimestamp: string): string {
  const parsed = new Date(isoTimestamp)
  return Number.isNaN(parsed.getTime()) ? isoTimestamp : parsed.toLocaleString()
}

/**
 * The editor workspace. This component owns the single ReportDetail for the
 * page; every child reports its result back through a callback and this
 * component replaces the state with the server's answer. There is no second
 * copy of the report anywhere, so there is nothing to keep in sync.
 */
export function ReportDetailPage() {
  const { reportId = '' } = useParams<{ reportId: string }>()
  // useCallback is mandatory: useAsyncResource treats load as an effect
  // dependency, so an inline arrow would refetch forever.
  const load = useCallback(() => getReport(reportId), [reportId])
  const {
    data: report,
    status,
    error,
    setData: setReport,
  } = useAsyncResource<ReportDetail>(load)

  const [reorderError, setReorderError] = useState<unknown>(null)

  const handleReorder = useCallback(
    async (fieldIds: string[]) => {
      // report only gates whether a reorder can happen at all (it is non-null
      // for the whole lifetime of this handler once the page has loaded, and
      // its id never changes), not the value being written -- so reading it
      // from this closure is safe here.
      if (report === null) {
        return
      }
      // Optimistic: show the dropped order at once, then let the server's
      // response be the authority. previous is captured from inside the
      // functional updater -- not from the `report` closure -- so it
      // reflects the true current state even if another update landed in
      // between (e.g. a field-content save that resolved while this drag
      // was in flight).
      //
      // The updater must run synchronously with flushSync: setReport does
      // not otherwise guarantee its updater has executed by the time this
      // function's next line runs, and previousReport would then still be
      // null when the catch block reads it, rolling the report back to null
      // instead of its pre-reorder value. This is not hypothetical --
      // without flushSync it reproduces deterministically under coverage
      // instrumentation, which changes React's scheduling enough to expose
      // the gap.
      let previousReport: ReportDetail | null = null
      setReorderError(null)
      flushSync(() => {
        setReport((prev) => {
          previousReport = prev
          return prev === null ? prev : withFieldOrder(prev, fieldIds)
        })
      })
      try {
        setReport(await reorderFields(report.id, fieldIds))
      } catch (caught: unknown) {
        setReport(previousReport)
        setReorderError(caught)
      }
    },
    [report, setReport],
  )

  // dnd-kit cannot complete a drag under jsdom (all measured rects are zero),
  // so the reorder path is unreachable from a test without this hook. It is
  // compiled out of any non-test mode, so production never listens.
  useEffect(() => {
    if (import.meta.env.MODE !== 'test') {
      return
    }
    function handleTestReorder(event: Event) {
      void handleReorder((event as CustomEvent<string[]>).detail)
    }
    window.addEventListener('test:reorder', handleTestReorder)
    return () => window.removeEventListener('test:reorder', handleTestReorder)
  }, [handleReorder])

  return (
    <section className="px-4 pb-8">
      <Link
        to="/reports"
        className="text-sm text-blue-royal underline hover:text-navy-dark"
      >
        Back to reports
      </Link>

      {status === 'loading' ? <p className="mt-4">Loading report...</p> : null}

      {status === 'error' ? (
        <div className="mt-4">
          <ErrorBanner error={error} />
        </div>
      ) : null}

      {status === 'ready' && report !== null ? (
        <div className="mt-2 flex flex-col gap-6">
          <div>
            <h2 className="text-xl font-semibold text-navy-deep">{report.name}</h2>
            <p className="text-sm text-grey-mid">
              Updated {formatTimestamp(report.updated_at)}
            </p>
          </div>

          <SourceDocumentPanel
            reportId={report.id}
            onGenerated={(generated) => setReport(generated)}
          />

          <LogoUploadPanel
            report={report}
            onUploaded={(updated) => setReport(updated)}
          />

          {report.fields.length === 0 ? (
            <p>This report has no fields yet.</p>
          ) : (
            <SortableFieldList
              fields={report.fields}
              onReorder={(fieldIds) => void handleReorder(fieldIds)}
              renderField={(field) => (
                <ReportFieldCard
                  reportId={report.id}
                  field={field}
                  onSaved={(saved) =>
                    setReport((prev) =>
                      prev === null ? prev : replaceField(prev, saved),
                    )
                  }
                  onDeleted={(fieldId) =>
                    setReport((prev) =>
                      prev === null ? prev : removeField(prev, fieldId),
                    )
                  }
                />
              )}
            />
          )}

          <ErrorBanner error={reorderError} onDismiss={() => setReorderError(null)} />

          <AddFieldForm
            reportId={report.id}
            onAdded={(added) =>
              setReport((prev) => (prev === null ? prev : appendField(prev, added)))
            }
          />
        </div>
      ) : null}
    </section>
  )
}

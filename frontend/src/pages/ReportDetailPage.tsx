import { useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getReport } from '../api/reports'
import type { ReportDetail } from '../api/types'
import { ReportFieldCard } from '../components/reports/ReportFieldCard'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { useAsyncResource } from '../hooks/useAsyncResource'
import { replaceField } from '../lib/reportState'

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

          {report.fields.length === 0 ? (
            <p>This report has no fields yet.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {report.fields.map((field) => (
                <li
                  key={field.id}
                  className="flex rounded-md border border-grey-light bg-white"
                >
                  <ReportFieldCard
                    reportId={report.id}
                    field={field}
                    onSaved={(saved) =>
                      setReport((prev) => (prev === null ? prev : replaceField(prev, saved)))
                    }
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </section>
  )
}

import { useCallback } from 'react'
import { Link } from 'react-router-dom'

import { listReports } from '../api/reports'
import type { ReportSummary } from '../api/types'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { useAsyncResource } from '../hooks/useAsyncResource'

/**
 * Timestamps arrive as microsecond-precision UTC ISO strings. They are shown
 * in the reader's own locale because "when did I last touch this" is the only
 * question this column answers.
 */
function formatTimestamp(isoTimestamp: string): string {
  const parsed = new Date(isoTimestamp)
  return Number.isNaN(parsed.getTime()) ? isoTimestamp : parsed.toLocaleString()
}

export function ReportsListPage() {
  // useCallback is mandatory here: useAsyncResource treats load as an effect
  // dependency, so an inline arrow would refetch on every render forever.
  const load = useCallback(() => listReports(), [])
  const { data, status, error } = useAsyncResource<ReportSummary[]>(load)
  const reports = data ?? []

  return (
    <section className="px-4 pb-8">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-navy-deep">Reports</h2>
        <Link
          to="/reports/new"
          className="inline-flex items-center rounded-md bg-navy-deep px-4 py-2 text-sm font-semibold text-white hover:bg-navy-dark"
        >
          New report
        </Link>
      </div>

      {status === 'loading' ? <p className="mt-4">Loading reports...</p> : null}

      {status === 'error' ? (
        <div className="mt-4">
          <ErrorBanner error={error} />
        </div>
      ) : null}

      {status === 'ready' && reports.length === 0 ? (
        <p className="mt-4">No reports yet.</p>
      ) : null}

      {status === 'ready' && reports.length > 0 ? (
        <ul className="mt-4 flex flex-col gap-2">
          {reports.map((report) => (
            <li
              key={report.id}
              className="rounded-md border border-grey-light bg-white px-4 py-3"
            >
              <Link
                to={`/reports/${report.id}`}
                className="font-semibold text-blue-royal underline hover:text-navy-dark"
              >
                {report.name}
              </Link>
              <p data-testid={`updated-${report.id}`} className="text-sm text-grey-mid">
                Updated {formatTimestamp(report.updated_at)}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

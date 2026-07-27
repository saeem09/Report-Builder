import { Link, useNavigate } from 'react-router-dom'

import { CreateReportForm } from '../components/reports/CreateReportForm'

export function CreateReportPage() {
  const navigate = useNavigate()

  return (
    <section className="px-4 pb-8">
      <Link
        to="/reports"
        className="text-sm text-blue-royal underline hover:text-navy-dark"
      >
        Back to reports
      </Link>
      <h2 className="mt-2 text-xl font-semibold text-navy-deep">New report</h2>
      <p className="mt-1 text-sm text-grey-mid">
        Name the report and optionally list the fields it should contain. Fields can be
        added, renamed by deleting and re-adding, reordered, and removed later.
      </p>
      <div className="mt-4 max-w-2xl">
        <CreateReportForm
          onCreated={(report) => {
            void navigate(`/reports/${report.id}`)
          }}
        />
      </div>
    </section>
  )
}

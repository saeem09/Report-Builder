import { Link, Route, Routes } from 'react-router-dom'

import { CreateReportPage } from './pages/CreateReportPage'
import { DiagramsListPage } from './pages/DiagramsListPage'
import { ReportsListPage } from './pages/ReportsListPage'

function App() {
  return (
    <main className="min-h-screen bg-grey-pale text-charcoal">
      <h1 className="text-navy-deep text-3xl font-bold p-4">Progress Report</h1>
      <nav className="flex gap-4 px-4 pb-4">
        <Link to="/reports" className="text-blue-royal hover:text-navy-dark underline">
          Reports
        </Link>
        <Link to="/diagrams" className="text-blue-royal hover:text-navy-dark underline">
          Diagrams
        </Link>
      </nav>
      <Routes>
        <Route path="/" element={<p className="px-4">Select Reports or Diagrams to get started.</p>} />
        <Route path="/reports/new" element={<CreateReportPage />} />
        <Route path="/reports" element={<ReportsListPage />} />
        <Route path="/diagrams" element={<DiagramsListPage />} />
      </Routes>
    </main>
  )
}

export default App

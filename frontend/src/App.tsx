import { Link, Route, Routes } from 'react-router-dom'

import { DiagramsListPage } from './pages/DiagramsListPage'
import { ReportsListPage } from './pages/ReportsListPage'

function App() {
  return (
    <main>
      <h1>Progress Report</h1>
      <nav>
        <Link to="/reports">Reports</Link>
        <Link to="/diagrams">Diagrams</Link>
      </nav>
      <Routes>
        <Route path="/" element={<p>Select Reports or Diagrams to get started.</p>} />
        <Route path="/reports" element={<ReportsListPage />} />
        <Route path="/diagrams" element={<DiagramsListPage />} />
      </Routes>
    </main>
  )
}

export default App

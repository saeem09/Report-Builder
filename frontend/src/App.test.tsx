import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import App from './App'
import * as reportsApi from './api/reports'

describe('App', () => {
  it('renders the app title and nav links', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Progress Report' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Reports' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Diagrams' })).toBeInTheDocument()
  })

  it('navigates to the reports page', async () => {
    vi.spyOn(reportsApi, 'listReports').mockResolvedValue([])

    render(
      <MemoryRouter initialEntries={['/reports']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Reports' })).toBeInTheDocument()
    vi.restoreAllMocks()
  })

  it('navigates to the diagrams page', () => {
    render(
      <MemoryRouter initialEntries={['/diagrams']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Diagrams' })).toBeInTheDocument()
  })

  it('renders the reports list route with data from the api', async () => {
    vi.spyOn(reportsApi, 'listReports').mockResolvedValue([])

    render(
      <MemoryRouter initialEntries={['/reports']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('No reports yet.')).toBeInTheDocument()
    vi.restoreAllMocks()
  })
})

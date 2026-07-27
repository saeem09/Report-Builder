import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import * as reportsApi from '../../api/reports'
import type { ReportField } from '../../api/types'
import { makeField } from '../../test/fixtures'
import { ReportFieldCard } from './ReportFieldCard'

function renderCard(field: ReportField, onSaved = vi.fn(), onDeleted = vi.fn()) {
  const view = render(
    <ReportFieldCard
      reportId="r1"
      field={field}
      onSaved={onSaved}
      onDeleted={onDeleted}
    />,
  )
  return { onSaved, onDeleted, rerender: view.rerender }
}

describe('ReportFieldCard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the label and the current content', () => {
    renderCard(makeField('f1', 'Summary', { content: 'We shipped it.' }))

    expect(screen.getByTestId('field-label')).toHaveTextContent('Summary')
    expect(screen.getByLabelText('Summary content')).toHaveValue('We shipped it.')
  })

  it('marks an untouched field with content as an AI draft', () => {
    renderCard(
      makeField('f1', 'Summary', { content: 'Drafted.', is_user_edited: false }),
    )

    expect(screen.getByText('AI draft')).toBeInTheDocument()
    expect(screen.queryByText('Edited by you')).toBeNull()
  })

  it('marks a user-edited field as edited by you', () => {
    renderCard(makeField('f1', 'Summary', { content: 'Mine.', is_user_edited: true }))

    expect(screen.getByText('Edited by you')).toBeInTheDocument()
    expect(screen.queryByText('AI draft')).toBeNull()
  })

  it('shows no badge on an empty untouched field', () => {
    renderCard(makeField('f1', 'Summary', { content: '', is_user_edited: false }))

    expect(screen.queryByText('AI draft')).toBeNull()
    expect(screen.queryByText('Edited by you')).toBeNull()
  })

  it('keeps Save disabled until the content changes', async () => {
    const user = userEvent.setup()
    renderCard(makeField('f1', 'Summary', { content: 'Draft.' }))

    expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()

    await user.type(screen.getByLabelText('Summary content'), '!')

    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled()
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
  })

  it('does not call the api while the user is typing', async () => {
    const user = userEvent.setup()
    const update = vi.spyOn(reportsApi, 'updateFieldContent')
    renderCard(makeField('f1', 'Summary'))

    await user.type(screen.getByLabelText('Summary content'), 'typed slowly')

    // Autosave is deliberately absent: PATCH sets is_user_edited permanently,
    // which excludes the field from all future AI generation.
    expect(update).not.toHaveBeenCalled()
  })

  it('saves on click and hands the updated field up', async () => {
    const user = userEvent.setup()
    const saved: ReportField = makeField('f1', 'Summary', {
      content: 'Mine.',
      is_user_edited: true,
    })
    const update = vi.spyOn(reportsApi, 'updateFieldContent').mockResolvedValue(saved)
    const { onSaved } = renderCard(makeField('f1', 'Summary'))

    await user.type(screen.getByLabelText('Summary content'), 'Mine.')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(update).toHaveBeenCalledWith('r1', 'f1', 'Mine.')
    })
    expect(onSaved).toHaveBeenCalledWith(saved)
  })

  it('shows a saving state while the request is in flight', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'updateFieldContent').mockReturnValue(new Promise(() => {}))
    renderCard(makeField('f1', 'Summary'))

    await user.type(screen.getByLabelText('Summary content'), 'x')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByRole('button', { name: 'Saving...' })).toBeDisabled()
  })

  it('reverts the draft back to the saved content', async () => {
    const user = userEvent.setup()
    renderCard(makeField('f1', 'Summary', { content: 'Draft.' }))

    await user.type(screen.getByLabelText('Summary content'), ' changed')
    await user.click(screen.getByRole('button', { name: 'Revert' }))

    expect(screen.getByLabelText('Summary content')).toHaveValue('Draft.')
    expect(screen.queryByText('Unsaved changes')).toBeNull()
  })

  it('surfaces a save failure and keeps the draft', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'updateFieldContent').mockRejectedValue(
      new ApiError(404, 'gone'),
    )
    const { onSaved } = renderCard(makeField('f1', 'Summary'))

    await user.type(screen.getByLabelText('Summary content'), 'Mine.')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That report or field no longer exists. Return to the reports list.',
    )
    expect(screen.getByLabelText('Summary content')).toHaveValue('Mine.')
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('keeps an unsaved edit when field.content changes underneath it (e.g. generation resolving mid-edit)', async () => {
    const user = userEvent.setup()
    const field = makeField('f1', 'Summary', { content: 'Original.' })
    const { rerender } = renderCard(field)

    await user.type(screen.getByLabelText('Summary content'), ' typed by me')

    // Simulate an unrelated mutation (AI generation) replacing the whole
    // report and handing this card a new field.content prop, before the user
    // has clicked Save.
    const regenerated = makeField('f1', 'Summary', { content: 'AI regenerated content.' })
    rerender(
      <ReportFieldCard
        reportId="r1"
        field={regenerated}
        onSaved={vi.fn()}
        onDeleted={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Summary content')).toHaveValue(
      'Original. typed by me',
    )
  })

  it('adopts a new field.content prop when the draft is not dirty', () => {
    const field = makeField('f1', 'Summary', { content: '' })
    const { rerender } = renderCard(field)

    // The user never touched this field, so draft still matches field.content.
    // Generation drafting it for the first time should flow through.
    const generated = makeField('f1', 'Summary', { content: 'AI drafted content.' })
    rerender(
      <ReportFieldCard
        reportId="r1"
        field={generated}
        onSaved={vi.fn()}
        onDeleted={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Summary content')).toHaveValue(
      'AI drafted content.',
    )
  })

  it('caps content at the server limit of 50000 characters', () => {
    renderCard(makeField('f1', 'Summary'))

    expect(screen.getByLabelText('Summary content')).toHaveAttribute(
      'maxLength',
      '50000',
    )
  })

  it('asks for confirmation before deleting', async () => {
    const user = userEvent.setup()
    const remove = vi.spyOn(reportsApi, 'deleteField')
    renderCard(makeField('f1', 'Summary'))

    await user.click(screen.getByRole('button', { name: 'Delete field' }))

    expect(screen.getByRole('dialog')).toHaveAccessibleName('Delete this field')
    expect(remove).not.toHaveBeenCalled()
  })

  it('deletes the field and hands its id up when confirmed', async () => {
    const user = userEvent.setup()
    const remove = vi.spyOn(reportsApi, 'deleteField').mockResolvedValue(undefined)
    const { onDeleted } = renderCard(makeField('f1', 'Summary'))

    await user.click(screen.getByRole('button', { name: 'Delete field' }))
    await user.click(screen.getByRole('button', { name: 'Delete field permanently' }))

    await waitFor(() => {
      expect(remove).toHaveBeenCalledWith('r1', 'f1')
    })
    expect(onDeleted).toHaveBeenCalledWith('f1')
  })

  it('does not delete when the confirmation is cancelled', async () => {
    const user = userEvent.setup()
    const remove = vi.spyOn(reportsApi, 'deleteField')
    const { onDeleted } = renderCard(makeField('f1', 'Summary'))

    await user.click(screen.getByRole('button', { name: 'Delete field' }))
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(remove).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it('surfaces a delete failure and closes the dialog', async () => {
    const user = userEvent.setup()
    vi.spyOn(reportsApi, 'deleteField').mockRejectedValue(new ApiError(404, 'gone'))
    const { onDeleted } = renderCard(makeField('f1', 'Summary'))

    await user.click(screen.getByRole('button', { name: 'Delete field' }))
    await user.click(screen.getByRole('button', { name: 'Delete field permanently' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'That report or field no longer exists. Return to the reports list.',
    )
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(onDeleted).not.toHaveBeenCalled()
  })
})

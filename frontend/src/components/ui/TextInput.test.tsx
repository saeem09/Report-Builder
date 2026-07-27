import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { TextInput } from './TextInput'

describe('TextInput', () => {
  it('associates the label with the input', () => {
    render(
      <TextInput id="report-name" label="Report name" value="" onChange={vi.fn()} />,
    )

    expect(screen.getByLabelText('Report name')).toHaveAttribute('id', 'report-name')
  })

  it('reports the typed value, not the event', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TextInput id="n" label="Name" value="" onChange={onChange} />)

    await user.type(screen.getByLabelText('Name'), 'K')

    expect(onChange).toHaveBeenCalledWith('K')
  })

  it('shows the current value', () => {
    render(<TextInput id="n" label="Name" value="Kickoff" onChange={vi.fn()} />)

    expect(screen.getByLabelText('Name')).toHaveValue('Kickoff')
  })

  it('passes through extra attributes such as maxLength and placeholder', () => {
    render(
      <TextInput
        id="n"
        label="Name"
        value=""
        onChange={vi.fn()}
        maxLength={200}
        placeholder="Sprint 4 progress"
      />,
    )

    const input = screen.getByLabelText('Name')
    expect(input).toHaveAttribute('maxLength', '200')
    expect(input).toHaveAttribute('placeholder', 'Sprint 4 progress')
  })
})

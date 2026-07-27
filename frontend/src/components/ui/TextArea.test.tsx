import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { TextArea } from './TextArea'

describe('TextArea', () => {
  it('associates the label with the textarea', () => {
    render(<TextArea id="c" label="Content" value="" onChange={vi.fn()} />)

    expect(screen.getByLabelText('Content')).toHaveAttribute('id', 'c')
  })

  it('reports the typed value', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TextArea id="c" label="Content" value="" onChange={onChange} />)

    await user.type(screen.getByLabelText('Content'), 'x')

    expect(onChange).toHaveBeenCalledWith('x')
  })

  it('defaults to six rows and accepts an override', () => {
    const { rerender } = render(
      <TextArea id="c" label="Content" value="" onChange={vi.fn()} />,
    )
    expect(screen.getByLabelText('Content')).toHaveAttribute('rows', '6')

    rerender(<TextArea id="c" label="Content" value="" onChange={vi.fn()} rows={2} />)
    expect(screen.getByLabelText('Content')).toHaveAttribute('rows', '2')
  })
})

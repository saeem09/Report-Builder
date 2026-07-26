import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Callout } from './Callout'

describe('Callout', () => {
  it('renders children inside the themed container', () => {
    render(<Callout>Hello</Callout>)

    const element = screen.getByText('Hello')
    expect(element.parentElement).toHaveClass('bg-tint-sky')
  })
})

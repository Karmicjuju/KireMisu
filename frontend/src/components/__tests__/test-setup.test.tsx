import React from 'react'
import { render, screen } from '@testing-library/react'

// Simple test to verify Jest and React Testing Library are working
describe('Test Setup', () => {
  it('can render a simple component', () => {
    const TestComponent = () => <div>Hello Test World</div>
    
    render(<TestComponent />)
    
    expect(screen.getByText('Hello Test World')).toBeInTheDocument()
  })

  it('has proper Jest matchers available', () => {
    expect(true).toBe(true)
    expect('hello').toMatch(/hello/)
    expect([1, 2, 3]).toHaveLength(3)
  })
})
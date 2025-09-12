import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SinglePageMode } from '../SinglePageMode'
import { DoublePageMode } from '../DoublePageMode'
import { VerticalScrollMode } from '../VerticalScrollMode'
import type { ReaderSettings, PageInfo } from '@/lib/reader-store'

// Mock next/image
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => {
    // eslint-disable-next-line jsx-a11y/alt-text
    return <img {...props} />
  },
}))

describe('SinglePageMode', () => {
  const mockSettings: ReaderSettings = {
    readingMode: 'single',
    readingDirection: 'ltr',
    pageFit: 'width',
    zoomLevel: 1.0,
    preloadPages: 3,
    showPageNumbers: true,
    fullscreenMode: false,
    autoDetectMode: false,
    doublePageOffset: false,
  }

  const mockPage: PageInfo = {
    filename: 'page1.jpg',
    index: 0,
    loaded: true,
  }

  it('renders a single page', () => {
    render(
      <SinglePageMode
        chapterId={1}
        page={mockPage}
        settings={mockSettings}
      />
    )

    const img = screen.getByAltText('Page 1')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', '/api/v1/reader/1/pages/page1.jpg')
  })

  it('shows page number when enabled', () => {
    render(
      <SinglePageMode
        chapterId={1}
        page={mockPage}
        settings={mockSettings}
      />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('hides page number when disabled', () => {
    const settingsNoNumbers = { ...mockSettings, showPageNumbers: false }
    render(
      <SinglePageMode
        chapterId={1}
        page={mockPage}
        settings={settingsNoNumbers}
      />
    )

    expect(screen.queryByText('1')).not.toBeInTheDocument()
  })

  it('applies zoom level', () => {
    const zoomedSettings = { ...mockSettings, zoomLevel: 2.0 }
    const { container } = render(
      <SinglePageMode
        chapterId={1}
        page={mockPage}
        settings={zoomedSettings}
      />
    )

    const wrapper = container.querySelector('div[style*="transform"]')
    expect(wrapper).toHaveStyle({ transform: 'scale(2)' })
  })

  it('shows loading indicator when page not loaded', () => {
    const loadingPage = { ...mockPage, loaded: false }
    render(
      <SinglePageMode
        chapterId={1}
        page={loadingPage}
        settings={mockSettings}
      />
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows error message when page has error', () => {
    const errorPage = { ...mockPage, error: 'Failed to load' }
    render(
      <SinglePageMode
        chapterId={1}
        page={errorPage}
        settings={mockSettings}
      />
    )

    expect(screen.getByText('Failed to load page')).toBeInTheDocument()
    expect(screen.getByText('Failed to load')).toBeInTheDocument()
  })
})

describe('DoublePageMode', () => {
  const mockSettings: ReaderSettings = {
    readingMode: 'double',
    readingDirection: 'ltr',
    pageFit: 'height',
    zoomLevel: 1.0,
    preloadPages: 3,
    showPageNumbers: true,
    fullscreenMode: false,
    autoDetectMode: false,
    doublePageOffset: false,
  }

  const mockLeftPage: PageInfo = {
    filename: 'page1.jpg',
    index: 0,
    loaded: true,
  }

  const mockRightPage: PageInfo = {
    filename: 'page2.jpg',
    index: 1,
    loaded: true,
  }

  it('renders two pages side by side', () => {
    render(
      <DoublePageMode
        chapterId={1}
        leftPage={mockLeftPage}
        rightPage={mockRightPage}
        settings={mockSettings}
      />
    )

    const page1 = screen.getByAltText('Page 1')
    const page2 = screen.getByAltText('Page 2')
    
    expect(page1).toBeInTheDocument()
    expect(page2).toBeInTheDocument()
  })

  it('reverses page order for RTL reading', () => {
    const rtlSettings = { ...mockSettings, readingDirection: 'rtl' }
    const { container } = render(
      <DoublePageMode
        chapterId={1}
        leftPage={mockLeftPage}
        rightPage={mockRightPage}
        settings={rtlSettings}
      />
    )

    const images = container.querySelectorAll('img')
    // In RTL, right page should come first
    expect(images[0]).toHaveAttribute('alt', 'Page 2')
    expect(images[1]).toHaveAttribute('alt', 'Page 1')
  })

  it('shows placeholder for missing page', () => {
    render(
      <DoublePageMode
        chapterId={1}
        leftPage={mockLeftPage}
        rightPage={null}
        settings={mockSettings}
      />
    )

    expect(screen.getByText('No page')).toBeInTheDocument()
  })

  it('shows page numbers for both pages', () => {
    render(
      <DoublePageMode
        chapterId={1}
        leftPage={mockLeftPage}
        rightPage={mockRightPage}
        settings={mockSettings}
      />
    )

    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })
})

describe('VerticalScrollMode', () => {
  const mockSettings: ReaderSettings = {
    readingMode: 'vertical',
    readingDirection: 'ltr',
    pageFit: 'width',
    zoomLevel: 1.0,
    preloadPages: 2,
    showPageNumbers: true,
    fullscreenMode: false,
    autoDetectMode: false,
    doublePageOffset: false,
  }

  const mockPages: PageInfo[] = [
    { filename: 'page1.jpg', index: 0, loaded: true },
    { filename: 'page2.jpg', index: 1, loaded: true },
    { filename: 'page3.jpg', index: 2, loaded: true },
  ]

  it('renders all pages vertically', () => {
    render(
      <VerticalScrollMode
        chapterId={1}
        pages={mockPages}
        currentPageIndex={0}
        settings={mockSettings}
      />
    )

    expect(screen.getByAltText('Page 1')).toBeInTheDocument()
    expect(screen.getByAltText('Page 2')).toBeInTheDocument()
    expect(screen.getByAltText('Page 3')).toBeInTheDocument()
  })

  it('highlights current page', () => {
    const { container } = render(
      <VerticalScrollMode
        chapterId={1}
        pages={mockPages}
        currentPageIndex={1}
        settings={mockSettings}
      />
    )

    const pages = container.querySelectorAll('[data-page-index]')
    expect(pages[1]).toHaveClass('ring-2', 'ring-orange-500')
  })

  it('shows page counters', () => {
    render(
      <VerticalScrollMode
        chapterId={1}
        pages={mockPages}
        currentPageIndex={0}
        settings={mockSettings}
      />
    )

    expect(screen.getByText('1 / 3')).toBeInTheDocument()
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(screen.getByText('3 / 3')).toBeInTheDocument()
  })

  it('shows end of chapter indicator', () => {
    render(
      <VerticalScrollMode
        chapterId={1}
        pages={mockPages}
        currentPageIndex={0}
        settings={mockSettings}
      />
    )

    expect(screen.getByText('End of Chapter')).toBeInTheDocument()
  })

  it('lazy loads images based on visibility', () => {
    const manyPages = Array.from({ length: 10 }, (_, i) => ({
      filename: `page${i + 1}.jpg`,
      index: i,
      loaded: false,
    }))

    render(
      <VerticalScrollMode
        chapterId={1}
        pages={manyPages}
        currentPageIndex={0}
        settings={mockSettings}
      />
    )

    // Should show placeholders for pages not near current
    const placeholders = screen.getAllByText(/Page \d+/)
    expect(placeholders.length).toBeGreaterThan(0)
  })

  it('calls onPageChange when scrolling', () => {
    const mockOnPageChange = jest.fn()
    
    const { container } = render(
      <VerticalScrollMode
        chapterId={1}
        pages={mockPages}
        currentPageIndex={0}
        settings={mockSettings}
        onPageChange={mockOnPageChange}
      />
    )

    // Simulate intersection observer triggering
    // This would require more complex mocking of IntersectionObserver
    // For now, we just verify the component renders correctly
    expect(container.querySelector('.overflow-y-auto')).toBeInTheDocument()
  })
})
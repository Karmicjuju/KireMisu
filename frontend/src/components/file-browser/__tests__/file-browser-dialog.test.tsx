import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FileBrowserDialog } from '../file-browser-dialog'
import * as api from '@/lib/api'
import { DirectoryBrowseResponse, DirectoryItem } from '@/lib/types'

// Mock the API module
jest.mock('@/lib/api')
const mockedApi = api as jest.Mocked<typeof api>

// Mock data
const mockDirectoryResponse: DirectoryBrowseResponse = {
  current_path: '/home/user',
  parent_path: '/home',
  items: [
    {
      name: 'Documents',
      path: '/home/user/Documents',
      is_directory: true,
      modified_at: '2024-01-01T10:00:00Z'
    },
    {
      name: 'test.txt',
      path: '/home/user/test.txt',
      is_directory: false,
      size: 1024,
      modified_at: '2024-01-01T12:00:00Z'
    }
  ],
  total_items: 2
}

const mockEmptyDirectoryResponse: DirectoryBrowseResponse = {
  current_path: '/empty',
  parent_path: '/home',
  items: [],
  total_items: 0
}

const mockRootDirectoryResponse: DirectoryBrowseResponse = {
  current_path: '/',
  parent_path: undefined,
  items: [
    {
      name: 'home',
      path: '/home',
      is_directory: true,
      modified_at: '2024-01-01T10:00:00Z'
    }
  ],
  total_items: 1
}

describe('FileBrowserDialog', () => {
  const mockOnSelectPath = jest.fn()
  const mockOnOpenChange = jest.fn()

  const defaultProps = {
    open: true,
    onOpenChange: mockOnOpenChange,
    onSelectPath: mockOnSelectPath,
    initialPath: '/home/user'
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockedApi.browseDirectory.mockResolvedValue(mockDirectoryResponse)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders the dialog when open', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      expect(screen.getByText('Choose a Folder')).toBeInTheDocument()
      expect(screen.getByText('Start typing or select path')).toBeInTheDocument()
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/home/user')
      })
    })

    it('does not render when closed', () => {
      render(<FileBrowserDialog {...defaultProps} open={false} />)
      
      expect(screen.queryByText('Choose a Folder')).not.toBeInTheDocument()
    })

    it('loads directory on open', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/home/user')
      })
    })

    it('displays loading state initially', () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })
  })

  describe('Directory Browsing', () => {
    it('displays directory items after loading', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
        expect(screen.getByText('test.txt')).toBeInTheDocument()
      })
    })

    it('shows parent directory navigation when available', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('..')).toBeInTheDocument()
      })
    })

    it('does not show parent directory navigation at root', async () => {
      mockedApi.browseDirectory.mockResolvedValue(mockRootDirectoryResponse)
      render(<FileBrowserDialog {...defaultProps} initialPath="/" />)
      
      await waitFor(() => {
        expect(screen.queryByText('..')).not.toBeInTheDocument()
      })
    })

    it('displays empty folder message when no items', async () => {
      mockedApi.browseDirectory.mockResolvedValue(mockEmptyDirectoryResponse)
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('This folder is empty')).toBeInTheDocument()
      })
    })

    it('shows directory icons for folders', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        const documentsItem = screen.getByText('Documents').closest('div')
        expect(documentsItem).toBeInTheDocument()
      })
    })

    it('displays file size for files', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('1 KB')).toBeInTheDocument()
      })
    })

    it('formats dates correctly', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Jan 1, 2024, 10:00 AM')).toBeInTheDocument()
      })
    })
  })

  describe('Navigation', () => {
    it('navigates to directory on double-click', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
      })

      const documentsItem = screen.getByText('Documents')
      await user.dblClick(documentsItem)
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/home/user/Documents')
      })
    })

    it('navigates to parent directory on double-click', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('..')).toBeInTheDocument()
      })

      const parentItem = screen.getByText('..')
      await user.dblClick(parentItem)
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/home')
      })
    })

    it('updates path input when navigating', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        const pathInput = screen.getByDisplayValue('/home/user')
        expect(pathInput).toBeInTheDocument()
      })
    })

    it('navigates using path input form', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        const pathInput = screen.getByDisplayValue('/home/user')
        expect(pathInput).toBeInTheDocument()
      })

      const pathInput = screen.getByDisplayValue('/home/user')
      await user.clear(pathInput)
      await user.type(pathInput, '/home/test')
      
      const goButton = screen.getByText('Go')
      await user.click(goButton)
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/home/test')
      })
    })

    it('submits path input form on enter', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        const pathInput = screen.getByDisplayValue('/home/user')
        expect(pathInput).toBeInTheDocument()
      })

      const pathInput = screen.getByDisplayValue('/home/user')
      await user.clear(pathInput)
      await user.type(pathInput, '/home/test')
      await user.keyboard('{Enter}')
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/home/test')
      })
    })
  })

  describe('Item Selection', () => {
    it('selects directory on single click', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
      })

      const documentsItem = screen.getByText('Documents')
      await user.click(documentsItem)
      
      expect(screen.getByText('Selected:')).toBeInTheDocument()
      expect(screen.getByText('/home/user/Documents')).toBeInTheDocument()
    })

    it('selects file on single click', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('test.txt')).toBeInTheDocument()
      })

      const fileItem = screen.getByText('test.txt')
      await user.click(fileItem)
      
      expect(screen.getByText('Selected:')).toBeInTheDocument()
      expect(screen.getByText('/home/user/test.txt')).toBeInTheDocument()
    })

    it('shows visual selection highlight', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
      })

      const documentsItem = screen.getByText('Documents').closest('div')
      await user.click(screen.getByText('Documents'))
      
      expect(documentsItem).toHaveClass('bg-accent')
    })
  })

  describe('Dialog Actions', () => {
    it('calls onSelectPath with selected path when Select Folder is clicked', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
      })

      // Select a directory
      await user.click(screen.getByText('Documents'))
      
      // Click Select Folder
      const selectButton = screen.getByText('Select Folder')
      await user.click(selectButton)
      
      expect(mockOnSelectPath).toHaveBeenCalledWith('/home/user/Documents')
      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })

    it('calls onSelectPath with current path when no selection', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
      })

      // Click Select Folder without selecting anything
      const selectButton = screen.getByText('Select Folder')
      await user.click(selectButton)
      
      expect(mockOnSelectPath).toHaveBeenCalledWith('/home/user')
      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })

    it('closes dialog when Cancel is clicked', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument()
      })

      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)
      
      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })

    it('enables Select Folder button when path is available', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        const selectButton = screen.getByText('Select Folder')
        expect(selectButton).not.toBeDisabled()
      })
    })
  })

  describe('Error Handling', () => {
    it('displays error message when directory loading fails', async () => {
      const errorMessage = 'Directory not found'
      mockedApi.browseDirectory.mockRejectedValue(new Error(errorMessage))
      
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
    })

    it('handles API error with custom message', async () => {
      mockedApi.browseDirectory.mockRejectedValue(new Error('Permission denied'))
      
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Permission denied')).toBeInTheDocument()
      })
    })

    it('shows generic error for unknown errors', async () => {
      mockedApi.browseDirectory.mockRejectedValue('Unknown error')
      
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Failed to load directory')).toBeInTheDocument()
      })
    })

    it('retries loading when path input is submitted after error', async () => {
      const user = userEvent.setup()
      
      // First call fails
      mockedApi.browseDirectory.mockRejectedValueOnce(new Error('Failed'))
      // Second call succeeds
      mockedApi.browseDirectory.mockResolvedValueOnce(mockDirectoryResponse)
      
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Failed')).toBeInTheDocument()
      })

      // Try again with path input
      const pathInput = screen.getByDisplayValue('/home/user')
      const goButton = screen.getByText('Go')
      await user.click(goButton)
      
      await waitFor(() => {
        expect(screen.getByText('Documents')).toBeInTheDocument()
      })
    })
  })

  describe('File Size Formatting', () => {
    it('formats bytes correctly', async () => {
      const responseWithSizes: DirectoryBrowseResponse = {
        current_path: '/test',
        items: [
          { name: 'small.txt', path: '/test/small.txt', is_directory: false, size: 100 },
          { name: 'medium.txt', path: '/test/medium.txt', is_directory: false, size: 2048 },
          { name: 'large.txt', path: '/test/large.txt', is_directory: false, size: 1048576 },
          { name: 'huge.txt', path: '/test/huge.txt', is_directory: false, size: 1073741824 }
        ],
        total_items: 4
      }
      
      mockedApi.browseDirectory.mockResolvedValue(responseWithSizes)
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('100 B')).toBeInTheDocument()
        expect(screen.getByText('2 KB')).toBeInTheDocument()
        expect(screen.getByText('1 MB')).toBeInTheDocument()
        expect(screen.getByText('1 GB')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels and roles', async () => {
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
        expect(screen.getByText('Choose a Folder')).toBeInTheDocument()
      })
    })

    it('supports keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByDisplayValue('/home/user')).toBeInTheDocument()
      })

      const pathInput = screen.getByDisplayValue('/home/user')
      
      // Should be focusable
      await user.click(pathInput)
      expect(pathInput).toHaveFocus()
    })
  })

  describe('Props Handling', () => {
    it('uses default initialPath when not provided', async () => {
      const propsWithoutInitialPath = {
        open: true,
        onOpenChange: mockOnOpenChange,
        onSelectPath: mockOnSelectPath
      }
      
      render(<FileBrowserDialog {...propsWithoutInitialPath} />)
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/')
      })
    })

    it('respects initialPath prop', async () => {
      render(<FileBrowserDialog {...defaultProps} initialPath="/custom/path" />)
      
      await waitFor(() => {
        expect(mockedApi.browseDirectory).toHaveBeenCalledWith('/custom/path')
      })
    })

    it('calls onOpenChange when dialog state changes', async () => {
      const user = userEvent.setup()
      render(<FileBrowserDialog {...defaultProps} />)
      
      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument()
      })

      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)
      
      expect(mockOnOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
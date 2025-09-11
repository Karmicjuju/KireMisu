import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LibraryPathsPage from '../page'
import * as api from '@/lib/api'
import { LibraryPathResponse, PathValidationResult, StorageInfo } from '@/lib/types'

// Mock the API module
jest.mock('@/lib/api')
const mockedApi = api as jest.Mocked<typeof api>

// Mock FileBrowserDialog component
jest.mock('@/components/file-browser/file-browser-dialog', () => ({
  FileBrowserDialog: ({ open, onSelectPath, onOpenChange }: any) => (
    open ? (
      <div data-testid="file-browser-dialog">
        <button onClick={() => onSelectPath('/selected/path')}>
          Select Path
        </button>
        <button onClick={() => onOpenChange(false)}>
          Close Browser
        </button>
      </div>
    ) : null
  )
}))

// Mock data
const mockLibraryPaths: LibraryPathResponse[] = [
  {
    id: 1,
    name: 'Main Library',
    path: '/home/user/manga',
    is_active: true,
    priority: 10,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z'
  },
  {
    id: 2,
    name: 'Secondary Library',
    path: '/home/user/manga2',
    is_active: false,
    priority: 5,
    created_at: '2024-01-02T10:00:00Z',
    updated_at: '2024-01-02T10:00:00Z'
  }
]

const mockValidationResult: PathValidationResult = {
  is_valid: true,
  exists: true,
  is_directory: true,
  is_readable: true,
  is_writable: true,
  error_message: null,
  total_space: 1000000000,
  free_space: 500000000
}

const mockInvalidValidationResult: PathValidationResult = {
  is_valid: false,
  exists: false,
  is_directory: false,
  is_readable: false,
  is_writable: false,
  error_message: 'Path does not exist',
  total_space: null,
  free_space: null
}

const mockStorageInfo: StorageInfo = {
  total_space: 1000000000,
  used_space: 600000000,
  free_space: 400000000,
  usage_percentage: 60.0
}

describe('LibraryPathsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockedApi.getLibraryPaths.mockResolvedValue(mockLibraryPaths)
    mockedApi.validatePath.mockResolvedValue(mockValidationResult)
    mockedApi.getStorageInfo.mockResolvedValue(mockStorageInfo)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Initial Rendering', () => {
    it('renders the page title and description', async () => {
      render(<LibraryPathsPage />)
      
      expect(screen.getByText('Library Paths')).toBeInTheDocument()
      expect(screen.getByText('Manage your manga library storage locations')).toBeInTheDocument()
    })

    it('displays loading state initially', () => {
      render(<LibraryPathsPage />)
      
      expect(screen.getByText('Loading library paths...')).toBeInTheDocument()
    })

    it('loads library paths on mount', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(mockedApi.getLibraryPaths).toHaveBeenCalledWith(true)
      })
    })

    it('displays refresh and add buttons', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument()
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })
    })
  })

  describe('Library Path Display', () => {
    it('displays library paths after loading', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
        expect(screen.getByText('Secondary Library')).toBeInTheDocument()
      })
    })

    it('shows active/inactive badges correctly', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument()
        expect(screen.getByText('Inactive')).toBeInTheDocument()
      })
    })

    it('displays priority badges', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Priority: 10')).toBeInTheDocument()
        expect(screen.getByText('Priority: 5')).toBeInTheDocument()
      })
    })

    it('shows path validation status', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getAllByText('Valid')).toHaveLength(2)
      })
    })

    it('displays storage information', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getAllByText('976.56 MB')).toHaveLength(2) // Total space
        expect(screen.getAllByText('572.2 MB')).toHaveLength(2)   // Used space
        expect(screen.getAllByText('381.47 MB')).toHaveLength(2)  // Free space
        expect(screen.getAllByText('60.0%')).toHaveLength(2)      // Usage percentage
      })
    })

    it('shows creation and update dates', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Created: 1/1/2024')).toBeInTheDocument()
        expect(screen.getByText('Created: 1/2/2024')).toBeInTheDocument()
      })
    })

    it('displays paths in monospace font', async () => {
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        const pathElement = screen.getByText('/home/user/manga')
        expect(pathElement.closest('div')).toHaveClass('font-mono')
      })
    })
  })

  describe('Empty State', () => {
    it('displays empty state when no library paths exist', async () => {
      mockedApi.getLibraryPaths.mockResolvedValue([])
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('No library paths configured')).toBeInTheDocument()
        expect(screen.getByText('Add your first library path to start managing your manga collection')).toBeInTheDocument()
      })
    })

    it('shows add button in empty state', async () => {
      mockedApi.getLibraryPaths.mockResolvedValue([])
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        const addButtons = screen.getAllByText('Add Library Path')
        expect(addButtons).toHaveLength(2) // One in header, one in empty state
      })
    })
  })

  describe('Add Library Path', () => {
    it('opens add dialog when add button is clicked', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('My Manga Library')).toBeInTheDocument()
    })

    it('validates form fields', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Try to submit empty form
      const submitButton = screen.getByRole('button', { name: /Add Library Path/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Name is required')).toBeInTheDocument()
        expect(screen.getByText('Path is required')).toBeInTheDocument()
      })
    })

    it('creates library path with valid data', async () => {
      const user = userEvent.setup()
      mockedApi.createLibraryPath.mockResolvedValue(mockLibraryPaths[0])
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Fill form
      await user.type(screen.getByPlaceholderText('My Manga Library'), 'Test Library')
      await user.type(screen.getByPlaceholderText('/path/to/manga/library'), '/test/path')
      await user.type(screen.getByDisplayValue('0'), '15')
      
      const submitButton = screen.getByRole('button', { name: /Add Library Path/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockedApi.createLibraryPath).toHaveBeenCalledWith({
          name: 'Test Library',
          path: '/test/path',
          is_active: true,
          priority: 15
        })
      })
    })

    it('opens file browser when folder button is clicked', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Click folder button
      const folderButton = screen.getByRole('button', { name: '' }) // Icon button
      await user.click(folderButton)
      
      expect(screen.getByTestId('file-browser-dialog')).toBeInTheDocument()
    })

    it('auto-generates name from selected path', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Open file browser and select path
      const folderButton = screen.getByRole('button', { name: '' })
      await user.click(folderButton)
      
      const selectPathButton = screen.getByText('Select Path')
      await user.click(selectPathButton)
      
      await waitFor(() => {
        expect(screen.getByDisplayValue('/selected/path')).toBeInTheDocument()
        expect(screen.getByDisplayValue('path')).toBeInTheDocument() // Auto-generated name
      })
    })

    it('closes dialog on successful creation', async () => {
      const user = userEvent.setup()
      mockedApi.createLibraryPath.mockResolvedValue(mockLibraryPaths[0])
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Fill and submit form
      await user.type(screen.getByPlaceholderText('My Manga Library'), 'Test Library')
      await user.type(screen.getByPlaceholderText('/path/to/manga/library'), '/test/path')
      
      const submitButton = screen.getByRole('button', { name: /Add Library Path/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.queryByText('Add Library Path')).not.toBeInTheDocument()
      })
    })

    it('handles creation errors', async () => {
      const user = userEvent.setup()
      mockedApi.createLibraryPath.mockRejectedValue(new Error('Path already exists'))
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Fill and submit form
      await user.type(screen.getByPlaceholderText('My Manga Library'), 'Test Library')
      await user.type(screen.getByPlaceholderText('/path/to/manga/library'), '/test/path')
      
      const submitButton = screen.getByRole('button', { name: /Add Library Path/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Path already exists')).toBeInTheDocument()
      })
    })
  })

  describe('Edit Library Path', () => {
    it('opens edit dialog when edit button is clicked', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const editButtons = screen.getAllByRole('button', { name: '' }) // Icon buttons
      const editButton = editButtons.find(button => 
        button.querySelector('svg[data-testid*="edit"]')
      )
      await user.click(editButton!)
      
      expect(screen.getByText('Edit Library Path')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Main Library')).toBeInTheDocument()
    })

    it('pre-fills form with existing data', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const editButtons = screen.getAllByRole('button', { name: '' })
      const editButton = editButtons.find(button => 
        button.querySelector('svg[data-testid*="edit"]')
      )
      await user.click(editButton!)
      
      expect(screen.getByDisplayValue('Main Library')).toBeInTheDocument()
      expect(screen.getByDisplayValue('/home/user/manga')).toBeInTheDocument()
      expect(screen.getByDisplayValue('10')).toBeInTheDocument()
      expect(screen.getByRole('checkbox')).toBeChecked()
    })

    it('disables path field in edit mode', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const editButtons = screen.getAllByRole('button', { name: '' })
      const editButton = editButtons.find(button => 
        button.querySelector('svg[data-testid*="edit"]')
      )
      await user.click(editButton!)
      
      const pathInput = screen.getByDisplayValue('/home/user/manga')
      expect(pathInput).toBeDisabled()
    })

    it('does not show file browser button in edit mode', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const editButtons = screen.getAllByRole('button', { name: '' })
      const editButton = editButtons.find(button => 
        button.querySelector('svg[data-testid*="edit"]')
      )
      await user.click(editButton!)
      
      // File browser button should not be present
      expect(screen.queryByTestId('file-browser-dialog')).not.toBeInTheDocument()
    })

    it('updates library path with modified data', async () => {
      const user = userEvent.setup()
      mockedApi.updateLibraryPath.mockResolvedValue(mockLibraryPaths[0])
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const editButtons = screen.getAllByRole('button', { name: '' })
      const editButton = editButtons.find(button => 
        button.querySelector('svg[data-testid*="edit"]')
      )
      await user.click(editButton!)
      
      // Modify form
      const nameInput = screen.getByDisplayValue('Main Library')
      await user.clear(nameInput)
      await user.type(nameInput, 'Updated Library')
      
      const priorityInput = screen.getByDisplayValue('10')
      await user.clear(priorityInput)
      await user.type(priorityInput, '20')
      
      const activeCheckbox = screen.getByRole('checkbox')
      await user.click(activeCheckbox) // Uncheck
      
      const updateButton = screen.getByRole('button', { name: /Update Library Path/i })
      await user.click(updateButton)
      
      await waitFor(() => {
        expect(mockedApi.updateLibraryPath).toHaveBeenCalledWith(1, {
          name: 'Updated Library',
          is_active: false,
          priority: 20
        })
      })
    })

    it('handles update errors', async () => {
      const user = userEvent.setup()
      mockedApi.updateLibraryPath.mockRejectedValue(new Error('Name already exists'))
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const editButtons = screen.getAllByRole('button', { name: '' })
      const editButton = editButtons.find(button => 
        button.querySelector('svg[data-testid*="edit"]')
      )
      await user.click(editButton!)
      
      const updateButton = screen.getByRole('button', { name: /Update Library Path/i })
      await user.click(updateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Name already exists')).toBeInTheDocument()
      })
    })
  })

  describe('Delete Library Path', () => {
    it('shows confirmation dialog before deleting', async () => {
      const user = userEvent.setup()
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true)
      mockedApi.deleteLibraryPath.mockResolvedValue(undefined)
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: '' })
      const deleteButton = deleteButtons.find(button => 
        button.querySelector('svg[data-testid*="trash"]')
      )
      await user.click(deleteButton!)
      
      expect(confirmSpy).toHaveBeenCalledWith(
        'Are you sure you want to delete this library path? This action cannot be undone.'
      )
      
      await waitFor(() => {
        expect(mockedApi.deleteLibraryPath).toHaveBeenCalledWith(1)
      })
      
      confirmSpy.mockRestore()
    })

    it('does not delete if user cancels confirmation', async () => {
      const user = userEvent.setup()
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false)
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: '' })
      const deleteButton = deleteButtons.find(button => 
        button.querySelector('svg[data-testid*="trash"]')
      )
      await user.click(deleteButton!)
      
      expect(mockedApi.deleteLibraryPath).not.toHaveBeenCalled()
      
      confirmSpy.mockRestore()
    })

    it('handles delete errors', async () => {
      const user = userEvent.setup()
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true)
      mockedApi.deleteLibraryPath.mockRejectedValue(new Error('Delete failed'))
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })

      const deleteButtons = screen.getAllByRole('button', { name: '' })
      const deleteButton = deleteButtons.find(button => 
        button.querySelector('svg[data-testid*="trash"]')
      )
      await user.click(deleteButton!)
      
      await waitFor(() => {
        expect(screen.getByText('Delete failed')).toBeInTheDocument()
      })
      
      confirmSpy.mockRestore()
    })
  })

  describe('Refresh Functionality', () => {
    it('reloads library paths when refresh button is clicked', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument()
      })

      const refreshButton = screen.getByText('Refresh')
      await user.click(refreshButton)
      
      expect(mockedApi.getLibraryPaths).toHaveBeenCalledTimes(2) // Once on mount, once on refresh
    })

    it('shows loading state during refresh', async () => {
      const user = userEvent.setup()
      
      // Make the API call hang
      let resolveApiCall: (value: any) => void
      mockedApi.getLibraryPaths.mockImplementation(() => 
        new Promise(resolve => { resolveApiCall = resolve })
      )
      
      render(<LibraryPathsPage />)
      
      const refreshButton = await screen.findByText('Refresh')
      await user.click(refreshButton)
      
      expect(screen.getByText('Loading library paths...')).toBeInTheDocument()
      
      // Resolve the API call
      resolveApiCall!(mockLibraryPaths)
    })
  })

  describe('Error Handling', () => {
    it('displays error message when loading fails', async () => {
      mockedApi.getLibraryPaths.mockRejectedValue(new Error('Network error'))
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })

    it('handles validation errors gracefully', async () => {
      mockedApi.validatePath.mockRejectedValue(new Error('Validation failed'))
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })
      
      // Error should be handled gracefully without crashing
      expect(screen.getByText('Main Library')).toBeInTheDocument()
    })

    it('handles storage info errors gracefully', async () => {
      mockedApi.getStorageInfo.mockRejectedValue(new Error('Storage info failed'))
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Main Library')).toBeInTheDocument()
      })
      
      // Error should be handled gracefully without crashing
      expect(screen.getByText('Main Library')).toBeInTheDocument()
    })

    it('displays validation error messages', async () => {
      mockedApi.validatePath.mockResolvedValue(mockInvalidValidationResult)
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getAllByText('Invalid')).toHaveLength(2)
        expect(screen.getAllByText('Path does not exist')).toHaveLength(2)
      })
    })
  })

  describe('Data Formatting', () => {
    it('formats byte sizes correctly', async () => {
      const storageWithDifferentSizes = {
        total_space: 1024,
        used_space: 512,
        free_space: 512,
        usage_percentage: 50.0
      }
      mockedApi.getStorageInfo.mockResolvedValue(storageWithDifferentSizes)
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getAllByText('1 KB')).toHaveLength(2) // Total space
        expect(screen.getAllByText('512 B')).toHaveLength(4) // Used and free space
      })
    })

    it('formats usage percentage correctly', async () => {
      const storageWithPrecisePercentage = {
        total_space: 1000,
        used_space: 333,
        free_space: 667,
        usage_percentage: 33.33
      }
      mockedApi.getStorageInfo.mockResolvedValue(storageWithPrecisePercentage)
      
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getAllByText('33.3%')).toHaveLength(2)
      })
    })
  })

  describe('Dialog Management', () => {
    it('closes dialog when cancel button is clicked', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)
      
      await waitFor(() => {
        expect(screen.queryByPlaceholderText('My Manga Library')).not.toBeInTheDocument()
      })
    })

    it('resets form when dialog is closed', async () => {
      const user = userEvent.setup()
      render(<LibraryPathsPage />)
      
      await waitFor(() => {
        expect(screen.getByText('Add Library Path')).toBeInTheDocument()
      })

      const addButton = screen.getAllByText('Add Library Path')[0]
      await user.click(addButton)
      
      // Fill form
      await user.type(screen.getByPlaceholderText('My Manga Library'), 'Test')
      
      // Close dialog
      const cancelButton = screen.getByText('Cancel')
      await user.click(cancelButton)
      
      // Reopen dialog
      await user.click(addButton)
      
      // Form should be reset
      expect(screen.getByPlaceholderText('My Manga Library')).toHaveValue('')
    })
  })
})
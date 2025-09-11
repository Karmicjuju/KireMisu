import * as api from '../api'

// Mock fetch globally
global.fetch = jest.fn()
const mockedFetch = fetch as jest.MockedFunction<typeof fetch>

// Mock localStorage
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
})

// Mock window.location
Object.defineProperty(window, 'location', {
  value: {
    href: '',
  },
  writable: true,
})

describe('API Functions', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue('mock-token')
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  describe('fetchWithAuth', () => {
    it('includes authorization header when token exists', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ data: 'test' }),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await api.getLibraryPaths()

      expect(mockedFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/library-paths?include_inactive=false',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
            'Content-Type': 'application/json',
          }),
        })
      )
    })

    it('does not include authorization header when no token', async () => {
      mockLocalStorage.getItem.mockReturnValue(null)
      
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ data: 'test' }),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await api.getLibraryPaths()

      expect(mockedFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/library-paths?include_inactive=false',
        expect.objectContaining({
          headers: expect.not.objectContaining({
            'Authorization': expect.any(String),
          }),
        })
      )
    })

    it('throws ApiError on HTTP error with detail message', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: jest.fn().mockResolvedValue({ detail: 'Bad request' }),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await expect(api.getLibraryPaths()).rejects.toThrow('Bad request')
    })

    it('throws ApiError on HTTP error without detail message', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        json: jest.fn().mockRejectedValue(new Error('Invalid JSON')),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await expect(api.getLibraryPaths()).rejects.toThrow('An error occurred')
    })

    it('includes status code in ApiError', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        json: jest.fn().mockResolvedValue({ detail: 'Not found' }),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      try {
        await api.getLibraryPaths()
      } catch (error: any) {
        expect(error.status).toBe(404)
        expect(error.message).toBe('Not found')
        expect(error.name).toBe('ApiError')
      }
    })
  })

  describe('Authentication API', () => {
    describe('login', () => {
      it('sends form data with correct headers', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ access_token: 'token', token_type: 'bearer' }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.login('testuser', 'testpass')

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/auth/login',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'username=testuser&password=testpass',
          }
        )
      })

      it('returns token data on successful login', async () => {
        const tokenData = { access_token: 'token123', token_type: 'bearer' }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(tokenData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.login('testuser', 'testpass')

        expect(result).toEqual(tokenData)
      })

      it('throws ApiError on invalid credentials', async () => {
        const mockResponse = {
          ok: false,
          status: 401,
          json: jest.fn().mockResolvedValue({ detail: 'Invalid credentials' }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await expect(api.login('wrong', 'credentials')).rejects.toThrow('Invalid credentials')
      })

      it('handles login errors gracefully', async () => {
        const mockResponse = {
          ok: false,
          status: 401,
          json: jest.fn().mockRejectedValue(new Error('Network error')),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await expect(api.login('user', 'pass')).rejects.toThrow('Invalid credentials')
      })
    })

    describe('logout', () => {
      it('removes token from localStorage and redirects', async () => {
        api.logout()

        expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('token')
        expect(window.location.href).toBe('/login')
      })
    })

    describe('getCurrentUser', () => {
      it('makes authenticated request to user endpoint', async () => {
        const userData = { id: 1, username: 'testuser' }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(userData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.getCurrentUser()

        expect(result).toEqual(userData)
        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/users/me',
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer mock-token',
            }),
          })
        )
      })
    })
  })

  describe('Library Paths API', () => {
    describe('getLibraryPaths', () => {
      it('makes request with default parameters', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue([]),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.getLibraryPaths()

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths?include_inactive=false',
          expect.any(Object)
        )
      })

      it('includes inactive paths when requested', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue([]),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.getLibraryPaths(true)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths?include_inactive=true',
          expect.any(Object)
        )
      })
    })

    describe('createLibraryPath', () => {
      it('sends POST request with library path data', async () => {
        const libraryPathData = {
          name: 'Test Library',
          path: '/test/path',
          is_active: true,
          priority: 5
        }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ id: 1, ...libraryPathData }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.createLibraryPath(libraryPathData)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify(libraryPathData),
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
            }),
          })
        )
      })

      it('returns created library path data', async () => {
        const libraryPathData = { name: 'Test', path: '/test' }
        const createdData = { id: 1, ...libraryPathData }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(createdData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.createLibraryPath(libraryPathData)

        expect(result).toEqual(createdData)
      })
    })

    describe('updateLibraryPath', () => {
      it('sends PUT request with update data', async () => {
        const updateData = { name: 'Updated Library', is_active: false }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ id: 1, ...updateData }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.updateLibraryPath(1, updateData)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/1',
          expect.objectContaining({
            method: 'PUT',
            body: JSON.stringify(updateData),
          })
        )
      })
    })

    describe('deleteLibraryPath', () => {
      it('sends DELETE request', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({}),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.deleteLibraryPath(1)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/1',
          expect.objectContaining({
            method: 'DELETE',
          })
        )
      })
    })

    describe('validatePath', () => {
      it('encodes path parameter correctly', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ is_valid: true }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.validatePath('/path/with spaces/and&symbols')

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/validate-path?path=%2Fpath%2Fwith%20spaces%2Fand%26symbols',
          expect.any(Object)
        )
      })
    })

    describe('browseDirectory', () => {
      it('encodes path and includes show_hidden parameter', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ current_path: '/test', items: [] }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.browseDirectory('/test/path', true)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/browse/%2Ftest%2Fpath?show_hidden=true',
          expect.any(Object)
        )
      })

      it('uses default show_hidden parameter', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ current_path: '/test', items: [] }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.browseDirectory('/test/path')

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/browse/%2Ftest%2Fpath?show_hidden=false',
          expect.any(Object)
        )
      })
    })

    describe('getStorageInfo', () => {
      it('makes request to storage info endpoint', async () => {
        const storageData = {
          total_space: 1000000000,
          used_space: 600000000,
          free_space: 400000000,
          usage_percentage: 60.0
        }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(storageData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.getStorageInfo(1)

        expect(result).toEqual(storageData)
        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/1/storage-info',
          expect.any(Object)
        )
      })
    })

    describe('activateLibraryPath', () => {
      it('sends PATCH request to activate endpoint', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ id: 1, is_active: true }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.activateLibraryPath(1)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/1/activate',
          expect.objectContaining({
            method: 'PATCH',
          })
        )
      })
    })

    describe('deactivateLibraryPath', () => {
      it('sends PATCH request to deactivate endpoint', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ id: 1, is_active: false }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.deactivateLibraryPath(1)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/1/deactivate',
          expect.objectContaining({
            method: 'PATCH',
          })
        )
      })
    })

    describe('updateLibraryPathPriority', () => {
      it('sends PATCH request with priority parameter', async () => {
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue({ id: 1, priority: 15 }),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        await api.updateLibraryPathPriority(1, 15)

        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library-paths/1/priority?new_priority=15',
          expect.objectContaining({
            method: 'PATCH',
          })
        )
      })
    })
  })

  describe('Library API', () => {
    describe('getLibrary', () => {
      it('makes authenticated request to library endpoint', async () => {
        const libraryData = { series: [], total_series: 0 }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(libraryData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.getLibrary()

        expect(result).toEqual(libraryData)
        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library',
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer mock-token',
            }),
          })
        )
      })
    })

    describe('getSeries', () => {
      it('makes request to series endpoint with ID', async () => {
        const seriesData = { id: 'series123', title: 'Test Series' }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(seriesData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.getSeries('series123')

        expect(result).toEqual(seriesData)
        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library/series/series123',
          expect.any(Object)
        )
      })
    })

    describe('getChapter', () => {
      it('makes request to chapter endpoint with ID', async () => {
        const chapterData = { id: 'chapter456', title: 'Test Chapter' }
        const mockResponse = {
          ok: true,
          json: jest.fn().mockResolvedValue(chapterData),
        }
        mockedFetch.mockResolvedValue(mockResponse as any)

        const result = await api.getChapter('chapter456')

        expect(result).toEqual(chapterData)
        expect(mockedFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/library/chapters/chapter456',
          expect.any(Object)
        )
      })
    })
  })

  describe('Error Handling', () => {
    it('handles network errors', async () => {
      mockedFetch.mockRejectedValue(new Error('Network error'))

      await expect(api.getLibraryPaths()).rejects.toThrow('Network error')
    })

    it('handles fetch errors that are not Response objects', async () => {
      mockedFetch.mockRejectedValue('String error')

      await expect(api.getLibraryPaths()).rejects.toBe('String error')
    })
  })

  describe('Environment Variables', () => {
    it('uses default API URL when environment variable is not set', async () => {
      delete process.env.NEXT_PUBLIC_API_URL
      
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue([]),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await api.getLibraryPaths()

      expect(mockedFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/library-paths?include_inactive=false',
        expect.any(Object)
      )
    })

    it('uses custom API URL from environment variable', async () => {
      const originalEnv = process.env.NEXT_PUBLIC_API_URL
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com'
      
      // Re-import the module to pick up the new environment variable
      jest.resetModules()
      const apiWithNewEnv = require('../api')
      
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue([]),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await apiWithNewEnv.getLibraryPaths()

      expect(mockedFetch).toHaveBeenCalledWith(
        'https://api.example.com/api/v1/library-paths?include_inactive=false',
        expect.any(Object)
      )
      
      // Restore original environment
      process.env.NEXT_PUBLIC_API_URL = originalEnv
    })
  })

  describe('Request Headers', () => {
    it('merges custom headers with default headers', async () => {
      // This would require access to internal fetchWithAuth function
      // For now, we test that the content-type is always set correctly
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({}),
      }
      mockedFetch.mockResolvedValue(mockResponse as any)

      await api.createLibraryPath({ name: 'Test', path: '/test' })

      expect(mockedFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
    })
  })
})
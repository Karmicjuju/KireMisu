const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  
  // Include cookies in request - this will send httpOnly auth cookie automatically
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: 'include', // Include cookies in requests
  })
  
  // Handle 401 responses by redirecting to login
  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new ApiError('Authentication required', 401)
  }
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'An error occurred' }))
    throw new ApiError(errorData.detail || 'Request failed', response.status)
  }
  
  return response.json()
}

export async function login(username: string, password: string) {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
    credentials: 'include', // Include cookies in login request
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Invalid credentials' }))
    throw new ApiError(errorData.detail || 'Login failed', response.status)
  }
  
  return response.json()
}

export async function logout() {
  try {
    // Call backend logout endpoint to clear httpOnly cookie
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
  } catch (error) {
    // Continue with logout even if API call fails
    console.warn('Logout API call failed:', error)
  }
  
  // Clear any remaining local storage (from old implementation)
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }
}

export async function getCurrentUser() {
  return fetchWithAuth('/api/v1/users/me')
}

export async function getLibrary() {
  return fetchWithAuth('/api/v1/library')
}

export async function getSeries(seriesId: string) {
  return fetchWithAuth(`/api/v1/library/series/${seriesId}`)
}

export async function getChapter(chapterId: string) {
  return fetchWithAuth(`/api/v1/library/chapters/${chapterId}`)
}
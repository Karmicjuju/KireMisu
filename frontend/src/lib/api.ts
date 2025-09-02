const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  })
  
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
  })
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Invalid credentials' }))
    throw new ApiError(errorData.detail || 'Login failed', response.status)
  }
  
  return response.json()
}

export async function logout() {
  localStorage.removeItem('token')
  window.location.href = '/login'
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
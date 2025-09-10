import DOMPurify from 'dompurify'

/**
 * Security utilities for input sanitization and validation
 * 
 * This module provides consistent security functions across the application
 * to prevent XSS, injection attacks, and ensure data integrity.
 */

// Input length limits for different field types
export const INPUT_LIMITS = {
  TITLE: 200,
  AUTHOR: 100,
  ARTIST: 100,
  DESCRIPTION: 2000,
  TAG: 50,
  GENRE: 30,
  URL: 2000,
  USERNAME: 50,
  PASSWORD: 128
} as const

/**
 * Sanitize text content to prevent XSS attacks
 * Removes all HTML tags while preserving text content
 */
export function sanitizeText(text: string): string {
  if (!text || typeof text !== 'string') return ''
  
  // Configure DOMPurify to allow only safe text content, no HTML tags
  const clean = DOMPurify.sanitize(text, { 
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
    KEEP_CONTENT: true // Keep text content, remove HTML tags
  })
  
  return clean.trim()
}

/**
 * Sanitize and validate an array of strings (genres, tags)
 */
export function sanitizeArray(arr: unknown): string[] {
  if (!Array.isArray(arr)) return []
  
  return arr
    .map(item => typeof item === 'string' ? sanitizeText(item) : '')
    .filter(item => item.length > 0)
    .slice(0, 20) // Limit array size to prevent DoS
}

/**
 * Validate and sanitize URL input
 */
export function sanitizeUrl(url: string, maxLength: number = INPUT_LIMITS.URL): string {
  if (!url || typeof url !== 'string') return ''
  
  const cleaned = sanitizeText(url)
  
  // Basic URL format validation
  if (cleaned.length > maxLength) return ''
  
  // Allow empty URLs (optional field)
  if (!cleaned) return ''
  
  // Basic URL pattern check
  const urlPattern = /^https?:\/\/.+/i
  if (!urlPattern.test(cleaned)) return ''
  
  return cleaned
}

/**
 * Validate and sanitize text input with length limits
 */
export function validateAndSanitizeText(
  text: string, 
  maxLength: number, 
  required: boolean = false
): string {
  if (!text || typeof text !== 'string') {
    return required ? '' : ''
  }
  
  const cleaned = sanitizeText(text)
  
  if (required && !cleaned) {
    throw new Error('Required field cannot be empty')
  }
  
  if (cleaned.length > maxLength) {
    throw new Error(`Text exceeds maximum length of ${maxLength} characters`)
  }
  
  return cleaned
}

/**
 * Validate email format (basic check)
 */
export function validateEmail(email: string): boolean {
  if (!email || typeof email !== 'string') return false
  
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailPattern.test(email.trim()) && email.length <= 254
}

/**
 * Validate username format
 */
export function validateUsername(username: string): boolean {
  if (!username || typeof username !== 'string') return false
  
  const cleaned = username.trim()
  
  // Username should be 3-50 characters, alphanumeric plus underscore and hyphen
  const usernamePattern = /^[a-zA-Z0-9_-]{3,50}$/
  return usernamePattern.test(cleaned)
}

/**
 * Sanitize form data for metadata editing
 */
export function sanitizeMetadataForm(data: any): any {
  if (!data || typeof data !== 'object') return {}
  
  return {
    title: validateAndSanitizeText(data.title, INPUT_LIMITS.TITLE, true),
    author: validateAndSanitizeText(data.author || '', INPUT_LIMITS.AUTHOR),
    artist: validateAndSanitizeText(data.artist || '', INPUT_LIMITS.ARTIST),
    description: validateAndSanitizeText(data.description || '', INPUT_LIMITS.DESCRIPTION),
    status: sanitizeText(data.status || ''),
    cover_url: sanitizeUrl(data.cover_url || ''),
    genres: sanitizeArray(data.genres).map(genre => 
      validateAndSanitizeText(genre, INPUT_LIMITS.GENRE)
    ),
    tags: sanitizeArray(data.tags).map(tag => 
      validateAndSanitizeText(tag, INPUT_LIMITS.TAG)
    )
  }
}

/**
 * Rate limiting helper for client-side protection
 */
class ClientRateLimit {
  private requests: Map<string, number[]> = new Map()
  
  isAllowed(key: string, maxRequests: number = 10, windowMs: number = 60000): boolean {
    const now = Date.now()
    const windowStart = now - windowMs
    
    // Get existing requests for this key
    const existing = this.requests.get(key) || []
    
    // Filter out old requests
    const recent = existing.filter(time => time > windowStart)
    
    // Check if under limit
    if (recent.length >= maxRequests) {
      return false
    }
    
    // Add current request
    recent.push(now)
    this.requests.set(key, recent)
    
    return true
  }
  
  reset(key: string): void {
    this.requests.delete(key)
  }
}

export const clientRateLimit = new ClientRateLimit()

/**
 * Escape special characters for use in RegExp
 */
export function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
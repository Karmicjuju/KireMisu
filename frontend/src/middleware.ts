import { NextRequest, NextResponse } from 'next/server'

// Protected routes that require authentication
const PROTECTED_ROUTES = [
  '/',
  '/library',
  '/settings', 
  '/profile'
]

// Public routes that don't require authentication
const PUBLIC_ROUTES = [
  '/login'
]

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Check if the current path is protected
  const isProtectedRoute = PROTECTED_ROUTES.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  )
  
  // Check if the current path is public
  const isPublicRoute = PUBLIC_ROUTES.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  )
  
  // Get token from cookies (FastAPI-Users cookie name)
  const token = request.cookies.get('kiremisu_auth')?.value
  
  // For protected routes, validate authentication by checking if token exists
  // We can't easily verify the JWT in middleware, so we trust the presence of the httpOnly cookie
  if (isProtectedRoute && !token) {
    const loginUrl = new URL('/login', request.url)
    // Store the attempted URL to redirect back after login
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }
  
  // If accessing login page while authenticated, redirect to home
  if (isPublicRoute && pathname === '/login' && token) {
    return NextResponse.redirect(new URL('/', request.url))
  }
  
  // Continue with the request
  return NextResponse.next()
}

// Configure which paths this middleware should run on
export const config = {
  // Match all paths except static files and API routes
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ]
}
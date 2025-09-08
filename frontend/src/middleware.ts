// Middleware temporarily disabled to eliminate console errors and RSC conflicts
// Authentication is handled purely client-side via ProtectedRoute components

import { NextRequest, NextResponse } from 'next/server'

export async function middleware(request: NextRequest) {
  // Allow all requests to pass through
  return NextResponse.next()
}

// Configure which paths this middleware should run on
export const config = {
  // Middleware disabled - no paths matched
  matcher: []
}
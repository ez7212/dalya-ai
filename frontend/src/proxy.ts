import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'

export async function proxy(request: NextRequest) {
  const response = NextResponse.next({
    request: { headers: request.headers },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()
  const { pathname } = request.nextUrl

  // Redirect to login if accessing protected routes without auth
  if (!user && (
    pathname.startsWith('/agent')
    || pathname.startsWith('/campaigns')
    || pathname.startsWith('/inbox')
    || pathname.startsWith('/listings')
    || pathname.startsWith('/pages')
    || pathname.startsWith('/settings')
    || pathname.startsWith('/onboarding')
    || pathname.startsWith('/dashboard')
    || pathname.startsWith('/seller-dashboard-archive')
    || pathname.startsWith('/admin')
  )) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Admin route protection
  if (pathname.startsWith('/admin') && user) {
    const adminId = process.env.ADMIN_USER_ID
    if (!adminId || user.id !== adminId) {
      return NextResponse.redirect(new URL('/agent', request.url))
    }
  }

  // Redirect logged-in users away from login page
  if (pathname === '/login' && user) {
    return NextResponse.redirect(new URL('/agent', request.url))
  }

  return response
}

export const config = {
  matcher: ['/agent/:path*', '/campaigns/:path*', '/inbox/:path*', '/listings/:path*', '/pages/:path*', '/settings/:path*', '/onboarding/:path*', '/dashboard/:path*', '/seller-dashboard-archive/:path*', '/sell/:path*', '/admin/:path*', '/login'],
}

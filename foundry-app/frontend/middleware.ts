import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = ['/login', '/callback', '/_next', '/favicon.ico']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  const token = request.cookies.get('id_token')?.value

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  try {
    const payloadB64 = token.split('.')[1]
    const payload = JSON.parse(
      Buffer.from(payloadB64, 'base64url').toString('utf-8')
    ) as { exp?: number }

    if (payload.exp && payload.exp < Date.now() / 1000) {
      const resp = NextResponse.redirect(new URL('/login', request.url))
      resp.cookies.delete('id_token')
      return resp
    }
  } catch {
    const resp = NextResponse.redirect(new URL('/login', request.url))
    resp.cookies.delete('id_token')
    return resp
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}

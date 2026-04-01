import { type NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = 'http://localhost:8000'

/**
 * Catch-all proxy for /api/v1/funds/* endpoints.
 * Reconstructs CNPJ (which contains '/') and forwards to FastAPI backend.
 *
 * Path patterns:
 *   /api/v1/funds/{cnpj_part1}/{cnpj_part2}/performance  → /api/v1/funds/{cnpj}/performance
 *   /api/v1/funds/{cnpj_part1}/{cnpj_part2}/daily         → /api/v1/funds/{cnpj}/daily
 *   /api/v1/funds/{cnpj_part1}/{cnpj_part2}/explanations  → /api/v1/funds/{cnpj}/explanations
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  const searchParams = request.nextUrl.searchParams.toString()

  // CNPJ format: XX.XXX.XXX/XXXX-XX — the '/' splits into 2 segments
  // So path = [cnpj_part1, cnpj_part2, endpoint?, ...]
  // Reconstruct: encode the CNPJ, keep the rest as-is
  let url: string

  if (path.length >= 3) {
    // e.g. ['43.121.002', '0001-41', 'performance']
    const cnpj = `${path[0]}/${path[1]}`
    const rest = path.slice(2).join('/')
    url = `${BACKEND_URL}/api/v1/funds/${encodeURIComponent(cnpj)}/${rest}`
  } else if (path.length === 2) {
    // Could be CNPJ only or segment/endpoint
    const cnpj = `${path[0]}/${path[1]}`
    url = `${BACKEND_URL}/api/v1/funds/${encodeURIComponent(cnpj)}`
  } else {
    url = `${BACKEND_URL}/api/v1/funds/${path.join('/')}`
  }

  if (searchParams) {
    url += `?${searchParams}`
  }

  try {
    const response = await fetch(url)
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch {
    return NextResponse.json(
      { error: 'Backend unreachable' },
      { status: 502 }
    )
  }
}

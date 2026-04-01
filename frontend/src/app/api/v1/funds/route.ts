import { NextResponse } from 'next/server'

const BACKEND_URL = 'http://localhost:8000'

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/funds`)
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: 'Backend unreachable' },
      { status: 502 }
    )
  }
}

import { getVisitorId } from './fingerprint'
import type { FeatureRequest, SortKey, VoteResult } from './types'

const JSON_HEADERS = { 'Content-Type': 'application/json' }

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
      else if (Array.isArray(body?.detail)) detail = body.detail[0]?.msg ?? detail
    } catch {
      /* body wasn't JSON — keep the generic message */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

// Voter identity rides in the X-Visitor-Id header (the browser fingerprint).
async function idHeaders(extra?: Record<string, string>): Promise<Record<string, string>> {
  return { 'X-Visitor-Id': await getVisitorId(), ...extra }
}

export async function listRequests(sort: SortKey): Promise<FeatureRequest[]> {
  const res = await fetch(`/api/requests?sort=${sort}`, { headers: await idHeaders() })
  return handle<FeatureRequest[]>(res)
}

export async function createRequest(input: {
  title: string
  description: string
}): Promise<FeatureRequest> {
  const res = await fetch('/api/requests', {
    method: 'POST',
    headers: await idHeaders(JSON_HEADERS),
    body: JSON.stringify(input),
  })
  return handle<FeatureRequest>(res)
}

// Toggles the caller's vote: DELETE if they've already voted, POST otherwise.
export async function castVote(id: number, currentlyVoted: boolean): Promise<VoteResult> {
  const res = await fetch(`/api/requests/${id}/vote`, {
    method: currentlyVoted ? 'DELETE' : 'POST',
    headers: await idHeaders(),
  })
  return handle<VoteResult>(res)
}

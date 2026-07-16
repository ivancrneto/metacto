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

export function listRequests(sort: SortKey): Promise<FeatureRequest[]> {
  return fetch(`/api/requests?sort=${sort}`, { credentials: 'include' }).then((res) =>
    handle<FeatureRequest[]>(res),
  )
}

export function createRequest(input: {
  title: string
  description: string
}): Promise<FeatureRequest> {
  return fetch('/api/requests', {
    method: 'POST',
    headers: JSON_HEADERS,
    credentials: 'include',
    body: JSON.stringify(input),
  }).then((res) => handle<FeatureRequest>(res))
}

// Toggles the caller's vote: DELETE if they've already voted, POST otherwise.
export function castVote(id: number, currentlyVoted: boolean): Promise<VoteResult> {
  return fetch(`/api/requests/${id}/vote`, {
    method: currentlyVoted ? 'DELETE' : 'POST',
    credentials: 'include',
  }).then((res) => handle<VoteResult>(res))
}

import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { castVote, createRequest, listRequests } from './api'
import type { FeatureRequest, SortKey } from './types'

const TITLE_MIN = 3
const TITLE_MAX = 120
const DESC_MAX = 5000

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function App() {
  const [requests, setRequests] = useState<FeatureRequest[]>([])
  const [sort, setSort] = useState<SortKey>('top')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const load = useCallback(async (which: SortKey) => {
    setLoading(true)
    setError(null)
    try {
      setRequests(await listRequests(which))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load requests')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(sort)
  }, [sort, load])

  // Optimistic vote: flip the UI immediately, reconcile with the server's count,
  // and roll back to the pre-click snapshot if the request fails.
  const handleVote = useCallback(
    async (target: FeatureRequest) => {
      setActionError(null)
      const snapshot = requests
      setRequests((prev) =>
        prev.map((r) =>
          r.id === target.id
            ? {
                ...r,
                has_voted: !r.has_voted,
                vote_count: r.vote_count + (r.has_voted ? -1 : 1),
              }
            : r,
        ),
      )
      try {
        const result = await castVote(target.id, target.has_voted)
        setRequests((prev) =>
          prev.map((r) =>
            r.id === target.id
              ? { ...r, vote_count: result.vote_count, has_voted: result.has_voted }
              : r,
          ),
        )
      } catch (e) {
        setRequests(snapshot)
        setActionError(e instanceof Error ? e.message : 'Your vote could not be saved')
      }
    },
    [requests],
  )

  const handleCreate = useCallback(
    async (input: { title: string; description: string }) => {
      await createRequest(input)
      await load(sort)
    },
    [load, sort],
  )

  const countLabel =
    requests.length > 0
      ? `${requests.length} request${requests.length === 1 ? '' : 's'}`
      : 'Requests'

  return (
    <div className="page">
      <header className="masthead">
        <h1>Feature Requests</h1>
        <p>Tell us what to build next — and upvote the ideas you want most.</p>
      </header>

      <SubmitForm onCreate={handleCreate} />

      <section className="board">
        <div className="board__bar">
          <h2>{countLabel}</h2>
          <div className="segmented" role="tablist" aria-label="Sort order">
            <button
              type="button"
              role="tab"
              aria-selected={sort === 'top'}
              className={sort === 'top' ? 'is-active' : ''}
              onClick={() => setSort('top')}
            >
              Top
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={sort === 'new'}
              className={sort === 'new' ? 'is-active' : ''}
              onClick={() => setSort('new')}
            >
              New
            </button>
          </div>
        </div>

        {actionError && (
          <div className="alert alert--warn" role="alert">
            {actionError}
          </div>
        )}

        {loading ? (
          <ListSkeleton />
        ) : error ? (
          <div className="alert alert--error" role="alert">
            {error}{' '}
            <button type="button" className="link" onClick={() => void load(sort)}>
              Retry
            </button>
          </div>
        ) : requests.length === 0 ? (
          <EmptyState />
        ) : (
          <ol className="list">
            {requests.map((r, i) => (
              <RequestCard key={r.id} rank={i + 1} request={r} onVote={handleVote} />
            ))}
          </ol>
        )}
      </section>

      <footer className="foot">
        Anonymous identity comes from a browser fingerprint — one vote per person per request.
      </footer>
    </div>
  )
}

function SubmitForm({
  onCreate,
}: {
  onCreate: (input: { title: string; description: string }) => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const trimmedTitle = title.trim()
  const trimmedDesc = description.trim()
  const valid =
    trimmedTitle.length >= TITLE_MIN &&
    trimmedTitle.length <= TITLE_MAX &&
    trimmedDesc.length >= 1 &&
    trimmedDesc.length <= DESC_MAX

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!valid || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await onCreate({ title: trimmedTitle, description: trimmedDesc })
      setTitle('')
      setDescription('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit your request')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="title">Title</label>
        <input
          id="title"
          value={title}
          maxLength={TITLE_MAX}
          placeholder="A short, specific summary"
          onChange={(e) => setTitle(e.target.value)}
        />
        <span className="counter">
          {trimmedTitle.length}/{TITLE_MAX}
        </span>
      </div>
      <div className="field">
        <label htmlFor="description">Description</label>
        <textarea
          id="description"
          value={description}
          maxLength={DESC_MAX}
          rows={3}
          placeholder="What problem would this solve, and for whom?"
          onChange={(e) => setDescription(e.target.value)}
        />
        <span className="counter">
          {trimmedDesc.length}/{DESC_MAX}
        </span>
      </div>
      {error && (
        <div className="alert alert--error" role="alert">
          {error}
        </div>
      )}
      <div className="form__actions">
        <button type="submit" className="btn btn--primary" disabled={!valid || submitting}>
          {submitting ? 'Submitting…' : 'Submit request'}
        </button>
      </div>
    </form>
  )
}

function RequestCard({
  rank,
  request,
  onVote,
}: {
  rank: number
  request: FeatureRequest
  onVote: (r: FeatureRequest) => void
}) {
  const voteTitle = request.is_author
    ? "You can't vote on your own request"
    : request.has_voted
      ? 'Remove your vote'
      : 'Upvote'

  return (
    <li className="card request">
      <button
        type="button"
        className={`vote ${request.has_voted ? 'vote--on' : ''}`}
        onClick={() => onVote(request)}
        disabled={request.is_author}
        title={voteTitle}
        aria-pressed={request.has_voted}
        aria-label={`Upvote "${request.title}" — ${request.vote_count} votes`}
      >
        <span className="vote__caret" aria-hidden>
          ▲
        </span>
        <span className="vote__count">{request.vote_count}</span>
      </button>
      <div className="request__body">
        <div className="request__head">
          <span className="rank">#{rank}</span>
          <h3>{request.title}</h3>
          {request.is_author && <span className="badge">Your request</span>}
        </div>
        <p className="request__desc">{request.description}</p>
        <div className="request__meta">{timeAgo(request.created_at)}</div>
      </div>
    </li>
  )
}

function ListSkeleton() {
  return (
    <ol className="list" aria-hidden>
      {[0, 1, 2].map((i) => (
        <li key={i} className="card request skeleton">
          <div className="vote skeleton__box" />
          <div className="request__body">
            <div className="skeleton__line skeleton__line--title" />
            <div className="skeleton__line" />
            <div className="skeleton__line skeleton__line--short" />
          </div>
        </li>
      ))}
    </ol>
  )
}

function EmptyState() {
  return (
    <div className="empty">
      <div className="empty__icon" aria-hidden>
        💡
      </div>
      <h3>No requests yet</h3>
      <p>Be the first to suggest something using the form above.</p>
    </div>
  )
}

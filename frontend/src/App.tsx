import { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";

import { ApiError, createRequest, listRequests, unvote, upvote } from "./api";
import { RequestCard } from "./components/RequestCard";
import { RequestForm } from "./components/RequestForm";
import { SortTabs } from "./components/SortTabs";
import { displayName } from "./displayName";
import { getVisitorId } from "./identity";
import { sortRequests } from "./sorting";
import type { FeatureRequest, SortMode } from "./types";

type DocumentWithVT = Document & {
  startViewTransition?: (callback: () => void) => void;
};

export function App() {
  // Identity is the device fingerprint (ADR-0004), resolved once on mount.
  const [identity, setIdentity] = useState<string | null>(null);
  const [sort, setSort] = useState<SortMode>("top");
  const [requests, setRequests] = useState<FeatureRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void getVisitorId().then(setIdentity);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listRequests(sort, identity);
      setRequests(page.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load requests");
    } finally {
      setLoading(false);
    }
  }, [sort, identity]);

  useEffect(() => {
    void load();
  }, [load]);

  // Commit a new ordering, animating the card movement when the browser supports
  // the View Transitions API (graceful instant fallback otherwise).
  const applyRequests = useCallback((next: FeatureRequest[]) => {
    const doc = document as DocumentWithVT;
    if (typeof doc.startViewTransition === "function") {
      doc.startViewTransition(() => flushSync(() => setRequests(next)));
    } else {
      setRequests(next);
    }
  }, []);

  const handleCreate = async (title: string, description: string) => {
    if (!identity) return;
    try {
      await createRequest(identity, title, description);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create request");
    }
  };

  const handleToggleVote = async (target: FeatureRequest) => {
    if (!identity) return;
    const snapshot = requests;
    // Optimistic update + re-sort so the card moves to its new rank immediately.
    const optimistic = sortRequests(
      requests.map((r) =>
        r.id === target.id
          ? {
              ...r,
              has_voted: !r.has_voted,
              vote_count: r.vote_count + (r.has_voted ? -1 : 1),
            }
          : r,
      ),
      sort,
    );
    applyRequests(optimistic);
    try {
      const updated = target.has_voted
        ? await unvote(identity, target.id)
        : await upvote(identity, target.id);
      // Reconcile with the authoritative row and re-sort again.
      applyRequests(
        sortRequests(
          optimistic.map((r) => (r.id === updated.id ? updated : r)),
          sort,
        ),
      );
    } catch (e) {
      applyRequests(snapshot); // rollback
      setError(e instanceof ApiError ? e.message : "Vote failed");
    }
  };

  return (
    <div className="app">
      <header className="app__header">
        <h1>Feature Requests</h1>
        <div className="identity">
          {identity ? (
            <span>
              You are <strong>{displayName(identity)}</strong>
            </span>
          ) : (
            <span className="muted">Identifying your device…</span>
          )}
        </div>
      </header>

      <RequestForm onSubmit={handleCreate} disabled={!identity} />
      <SortTabs sort={sort} onChange={setSort} />

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : requests.length === 0 ? (
        <p className="muted">No feature requests yet. Be the first!</p>
      ) : (
        <ul className="list">
          {requests.map((r) => (
            <RequestCard
              key={r.id}
              request={r}
              currentUser={identity ?? ""}
              onToggleVote={handleToggleVote}
            />
          ))}
        </ul>
      )}

      <footer className="app__footer muted">
        Signed in as <strong>{identity ? displayName(identity) : "…"}</strong> · sorted by {sort}
      </footer>
    </div>
  );
}

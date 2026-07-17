import { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";

import { ApiError, createRequest, listRequests, unvote, upvote } from "./api";
import { RequestCard } from "./components/RequestCard";
import { RequestForm } from "./components/RequestForm";
import { SortTabs } from "./components/SortTabs";
import { UserBar } from "./components/UserBar";
import { sortRequests } from "./sorting";
import type { FeatureRequest, SortMode } from "./types";

const USER_KEY = "feature-board-user";

type DocumentWithVT = Document & {
  startViewTransition?: (callback: () => void) => void;
};

export function App() {
  const [user, setUser] = useState<string>(() => localStorage.getItem(USER_KEY) ?? "");
  const [sort, setSort] = useState<SortMode>("top");
  const [requests, setRequests] = useState<FeatureRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    localStorage.setItem(USER_KEY, user);
  }, [user]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listRequests(sort, user || null);
      setRequests(page.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load requests");
    } finally {
      setLoading(false);
    }
  }, [sort, user]);

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
    if (!user) {
      setError("Set a username first.");
      return;
    }
    try {
      await createRequest(user, title, description);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create request");
    }
  };

  const handleToggleVote = async (target: FeatureRequest) => {
    if (!user) {
      setError("Set a username first.");
      return;
    }
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
        ? await unvote(user, target.id)
        : await upvote(user, target.id);
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
        <UserBar user={user} onChange={setUser} />
      </header>

      <RequestForm onSubmit={handleCreate} disabled={!user} />
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
              currentUser={user}
              onToggleVote={handleToggleVote}
            />
          ))}
        </ul>
      )}

      <footer className="app__footer muted">
        Signed in as <strong>{user || "nobody"}</strong> · sorted by {sort}
      </footer>
    </div>
  );
}

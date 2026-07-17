import type { FeatureRequest, Page, SortMode } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8010";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, user: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (user) headers.set("X-User", user);
  if (init.body) headers.set("Content-Type", "application/json");

  const resp = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const detail = typeof body?.detail === "string" ? body.detail : resp.statusText;
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export function listRequests(sort: SortMode, user: string | null): Promise<Page> {
  return request<Page>(`/feature-requests?sort=${sort}&page_size=50`, user);
}

export function createRequest(
  user: string,
  title: string,
  description: string,
): Promise<FeatureRequest> {
  return request<FeatureRequest>("/feature-requests", user, {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
}

export function upvote(user: string, id: number): Promise<FeatureRequest> {
  return request<FeatureRequest>(`/feature-requests/${id}/votes`, user, {
    method: "POST",
  });
}

export function unvote(user: string, id: number): Promise<FeatureRequest> {
  return request<FeatureRequest>(`/feature-requests/${id}/votes`, user, {
    method: "DELETE",
  });
}

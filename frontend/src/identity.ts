import FingerprintJS from "@fingerprintjs/fingerprintjs";

// Device-fingerprint identity (ADR-0004). The visitor id is a stable-ish hash of
// device/browser signals, giving better multi-vote deterrence than a self-chosen
// name. It is NOT a hard identity guarantee — open-source fingerprints can drift
// or collide. If fingerprinting is blocked, fall back to a persisted random id so
// the app still works (unique per browser via localStorage).

const FALLBACK_KEY = "feature-board-fallback-id";
let cached: Promise<string> | null = null;

async function compute(): Promise<string> {
  try {
    const agent = await FingerprintJS.load();
    const { visitorId } = await agent.get();
    return visitorId;
  } catch {
    let id = localStorage.getItem(FALLBACK_KEY);
    if (!id) {
      id = `fallback${Math.random().toString(36).slice(2, 12)}`;
      localStorage.setItem(FALLBACK_KEY, id);
    }
    return id;
  }
}

/** Resolve this device's identity, computing it once and caching the promise. */
export function getVisitorId(): Promise<string> {
  cached ??= compute();
  return cached;
}

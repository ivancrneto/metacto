import FingerprintJS from '@fingerprintjs/fingerprintjs'

// Load the FingerprintJS agent and compute the stable visitorId exactly once, at
// module load (app startup). Every caller awaits the same in-flight promise, so
// we never recompute the fingerprint per request.
const visitorIdPromise: Promise<string> = FingerprintJS.load()
  .then((agent) => agent.get())
  .then((result) => result.visitorId)

export function getVisitorId(): Promise<string> {
  return visitorIdPromise
}

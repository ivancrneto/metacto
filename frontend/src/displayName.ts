/**
 * Humanize an identity for display. Device-fingerprint identities are long
 * alphanumeric hashes, shown as "anon-<6 chars>"; short human handles (e.g. the
 * seeded "ada") are shown as-is.
 */
export function displayName(id: string): string {
  if (/^[a-z0-9]{16,}$/.test(id)) return `anon-${id.slice(0, 6)}`;
  return id;
}

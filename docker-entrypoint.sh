#!/bin/sh
set -e

# The data directory may be a freshly-mounted, root-owned volume. Make it
# writable by the unprivileged app user, then drop privileges to run the app.
mkdir -p /data
chown -R appuser:appuser /data 2>/dev/null || true

exec gosu appuser "$@"

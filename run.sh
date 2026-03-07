#!/bin/sh
# Single entry point — delegates to run.py (works on macOS and Windows).
cd "$(dirname "$0")"
exec python3 run.py "$@"

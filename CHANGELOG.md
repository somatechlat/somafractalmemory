# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Fix: `eventing/producer.py` now emits ISO8601 UTC timestamps to conform with `schemas/memory.event.json`.
- Fix: `workers/kv_writer.py` normalises incoming `timestamp` values (accepts numeric epoch and ISO strings) to preserve compatibility.
- Docs: Added `docs/PRODUCTION_READINESS.md` and linked it from canonical docs and README.

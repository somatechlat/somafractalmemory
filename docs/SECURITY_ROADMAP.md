# Security & Model-Download Roadmap

This document explains the small, non-invasive safety and reproducibility changes made on
`feature/safety-eviction-enterprise` and the recommended next steps.

## Goals

- Keep the system secure-by-default without changing algorithmic behavior or math.
- Make decisions explicit and auditable via environment variables.
- Reduce noisy Bandit findings while preserving developer convenience.

## Decisions implemented (non-regressive)

1. HF model download policy
   - Default: do not perform unpinned HF model downloads.
   - If `SOMA_MODEL_REV` is set, the code will load that exact revision.
   - If `SOMA_ALLOW_UNPINNED_HF=true`, unpinned HF downloads are allowed (developer opt-in).
   - Rationale: unpinned downloads are a supply-chain/reproducibility risk; this keeps the default secure.

2. Pickle gating
   - Pickle usage remains gated by `SOMA_ALLOW_PICKLE=true` and imports are annotated with `# nosec B403`.
   - A startup warning is logged when `SOMA_ALLOW_PICKLE=true` to inform admins.
   - Rationale: pickle is inherently unsafe for untrusted data; gating reduces accidental exposure.

3. Narrowed exception handling
   - Replaced `except Exception:`/`except:` in several best-effort parsing/fallback sites with
     targeted exceptions (TypeError, ValueError, AttributeError, OSError) and debug logs.
   - Rationale: retains robustness while avoiding masking programming errors and quieting Bandit.

4. Logging changes
   - Converted diagnostic f-strings that triggered false positives to parameterized logging where feasible.
   - Rationale: reduces static-analysis false positives without altering messages.

## Next recommended steps (non-invasive)

- CI: add Bandit run to CI and fail only on high severity issues. Document acceptable warnings in a security checklist.
- Replace pickle fallback with msgpack or a schema-backed binary format for improved safety (optional, medium effort).
- Consider adding a `SOMA_SECURITY_PROFILE` (dev/secure/enterprise) to centralize security opt-ins.

## How to opt-in for development convenience

- Temporarily allow HF auto-downloads (developer machine):

  export SOMA_ALLOW_UNPINNED_HF=true

- Temporarily enable pickle (trusted environment only):

  export SOMA_ALLOW_PICKLE=true

## Files changed in this branch (local)

- `somafractalmemory/somafractalmemory/core.py` — added opt-in checks for unpinned HF downloads and narrowed excepts.
- `somafractalmemory/somafractalmemory/implementations/providers.py` — added opt-in pin handling for from_pretrained.
- `docs/SECURITY_ROADMAP.md` — this file.
- `ARCHITECTURE.md` — appended short summary.

## Verification

- Bandit was run against `somafractalmemory` package during development; remaining medium findings are documented and relate to gated pickle or explicit opt-ins.
- Full test suite was run locally; all tests passed.

---

If you'd like, I can now:
- Commit these docs changes (I will commit locally on the feature branch),
- Prepare a PR draft text outlining the security decisions (no push), or
- Implement the optional next step to replace pickle with msgpack.

Which should I do next?

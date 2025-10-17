# Environment Setup

1. Request access to the GitHub repository and production secrets.
2. Follow the [Local Development Setup](../development-manual/local-setup.md).
3. Install tooling:
   - `pre-commit install`
   - `npm install -g markdownlint-cli2` (for documentation linting)
4. Run the smoke test:
   ```bash
   ./scripts/smoke.sh
   ```
5. Log into the staging cluster (if applicable) and verify you can reach `/health`.

If any step fails, consult the [Troubleshooting guide](resources/troubleshooting.md) or ask in `#somafractalmemory-dev`.

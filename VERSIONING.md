VERSIONING

This project follows Semantic Versioning (SemVer): MAJOR.MINOR.PATCH.

- MAJOR: incompatible API changes.
- MINOR: new backward-compatible functionality.
- PATCH: backward-compatible bug fixes.

Pre-release versions should use hyphenated identifiers (e.g. 1.0.0-alpha.1).
Build metadata may be appended with a plus sign (e.g. 1.0.0+20250902) but is not used for precedence.

Release workflow (recommended):

1. Update `pyproject.toml` version to the new release number.
2. Run full test suite and linters in CI; ensure green.
3. Create a release-prep commit with a clear message (e.g. `chore(release): prepare v1.0.0`).
4. Create an annotated tag matching the version: `git tag -a v1.0.0 -m "Release v1.0.0"`.
5. Push commit and tag: `git push origin master && git push origin v1.0.0`.
6. Publish a GitHub Release using the tag and include changelog/release notes.

Notes:
- Keep `pyproject.toml` as the single source of truth for the package version.
- Prefer creating tags from CI once checks pass, rather than from local machines, to ensure reproducibility.
- Consider using Conventional Commits + semantic-release or standard-version to automate changelog generation and tagging.

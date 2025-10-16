# Changelog

All notable changes to Soma Fractal Memory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Hash-based vector embeddings
- Memory importance scaling
- Redis caching layer

### Changed
- Improved PostgreSQL connection handling
- Updated documentation structure

### Fixed
- Database authentication issues
- Memory leak in vector search

## [0.2.0] - 2025-10-15

### Added
- Vector similarity search
- Importance-based memory pruning
- Health check endpoints
- Prometheus metrics

### Changed
- Upgraded to PostgreSQL 15
- Improved memory storage efficiency
- Enhanced API documentation

### Deprecated
- Legacy memory format
- Python 3.9 support

### Fixed
- Connection pool exhaustion
- Memory leak in long-running processes

## [0.1.0] - 2025-09-01

### Added
- Initial release
- Basic memory storage and retrieval
- REST API
- Docker support

### Security
- Basic authentication
- TLS support

[Unreleased]: https://github.com/somatechlat/somafractalmemory/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/somatechlat/somafractalmemory/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/somatechlat/somafractalmemory/releases/tag/v0.1.0

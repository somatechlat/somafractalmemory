# SomaFractalMemory User Manual

This manual explains how operators and product stakeholders interact with the SomaFractalMemory service from an end-user perspective. It focuses on the four supported workflows that every client or integration must follow:

1. **Store** a memory with `POST /memories`.
2. **Retrieve** a specific memory with `GET /memories/{coord}`.
3. **Search** across stored memories with `POST /memories/search` or `GET /memories/search`.
4. **Delete** a memory with `DELETE /memories/{coord}`.

The user manual is organised as follows:

- [Installation](installation.md): lightweight steps to run the HTTP API locally.
- [Quick-Start Tutorial](quick-start-tutorial.md): a guided flow that exercises the full lifecycle.
- [Feature Guides](features/): task-based walkthroughs for storage and search scenarios.
- [FAQ](faq.md): answers to the most common usability questions.

> **Important:** All legacy HTTP endpoints (`/store`, `/recall`, `/link`, graph routes, batch variants) are removed as of version 2.0.0. Every client must migrate and exclusively use the `/memories` surface described in this manual.

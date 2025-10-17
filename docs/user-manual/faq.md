---
title: "Frequently Asked Questions"
purpose: "**Q: Which endpoints are supported?** A: Only the `/memories` family plus public operational probes."
audience:
  - "End Users"
last_updated: "2025-10-16"
---

# Frequently Asked Questions

**Q: Which endpoints are supported?**
A: Only the `/memories` family plus public operational probes. All legacy routes (`/store`, `/recall`, `/link`, graph operations, batch variants) are removed.

**Q: Do I need a token for `GET /stats` or `GET /health`?**
A: No. Operational probes remain public but are rate limited. Every `/memories` request requires a Bearer token.

**Q: How do I update a memory?**
A: Re-post to `POST /memories` with the same `coord` string. The service overwrites the previous payload atomically.

**Q: What coordinate format should I use?**
A: Coordinates are comma-separated floats (e.g., `"1.2,3.4"`). Store the canonical string returned by the API.

**Q: Can I search by metadata only?**
A: Yes. Provide an empty query (`""`) plus the desired `filters`. The vector engine returns matches filtered on metadata.

**Q: Is there graph traversal?**
A: No. Graph operations were decommissioned. Build higher-level relationships in your application using coordinates if required.

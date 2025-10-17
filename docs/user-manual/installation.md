---
title: "Installation Guide"
purpose: "Step-by-step instructions for running the SomaFractalMemory HTTP API locally"
audience:
  - "End users"
  - "Product managers"
last_updated: "2025-10-17"
---

# Installation Guide

Follow these steps to run the SomaFractalMemory HTTP API on your workstation for evaluation or manual testing.

## Prerequisites
- Docker Desktop 4.28+ (or Docker Engine 24+)
- `docker compose` plugin (bundled with Docker Desktop)
- 4 CPU cores and 4 GB RAM available
- 10 GB free disk space
- A shell with `curl` (macOS and most Linux distributions ship with it by default)

## Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/somatechlat/somafractalmemory.git
   cd somafractalmemory
   ```

2. **Copy the environment template**
   ```bash
   cp .env.template .env
   ```
   Edit `.env` and set `SOMA_API_TOKEN` to any value you control. The remaining credentials are scoped for development only.

3. **Start the services**
   ```bash
   docker compose up --build -d
   ```
   This builds the API image and launches Postgres, Redis, Qdrant, and the HTTP API in the background.

4. **Verify the deployment**
   ```bash
   curl http://127.0.0.1:9595/health
   curl -H "Authorization: Bearer $(grep SOMA_API_TOKEN .env | cut -d'=' -f2)" \
     http://127.0.0.1:9595/stats
   ```
   Both commands should return HTTP `200` once the services finish initialising.

5. **Run the automated smoke test (optional)**
   ```bash
   make test-e2e
   ```
   The test stores and retrieves a memory, confirming that all backing services are connected.

6. **Stop the stack (optional)**
   ```bash
   docker compose down
   ```

## Configuration
Use the `.env.template` file as the canonical source for development defaults. Replace every credential before deploying to production or sharing access outside your workstation.

## Next Steps
- [Complete the Quick Start Tutorial](quick-start-tutorial.md)
- [Explore the feature guides](features/)
- [Read the FAQ](faq.md)

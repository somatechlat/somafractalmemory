# Installation Guide# Installation Guide



Follow these steps to run the SomaFractalMemory HTTP API locally for evaluation and manual testing.## Prerequisites



## Prerequisites- Docker and Docker Compose

- 4GB+ RAM

- macOS 13+ or Linux with Docker Desktop 4.28+.- 10GB+ free disk space

- `docker compose` plugin (bundled with Docker Desktop).

- A shell with `curl` (default on macOS/Linux).## Installation Steps



## Steps### 1. Using Docker Compose (Recommended)



1. **Clone the repository**```bash

   # Clone the repository

   ```bashgit clone https://github.com/somatechlat/somafractalmemory.git

   git clone https://github.com/somatechlat/somafractalmemory.gitcd somafractalmemory

   cd somafractalmemory

   ```# Start the services

docker compose up -d

2. **Copy the sample environment file**```



   ```bash### 2. Verifying Installation

   cp .env.example .env

   ``````bash

   # Check if services are running

   Set the required token that is used by the HTTP API:docker compose ps



   ```bash# Test the health endpoint

   echo "SOMA_API_TOKEN=local-dev-token" >> .envcurl http://localhost:9595/health

   ``````



3. **Start the stack**## Configuration



   ```bashThe system can be configured through environment variables or a config file. See [Configuration Reference](../technical-manual/configuration.md) for details.

   docker compose up -d

   ```## Next Steps



   The HTTP API is now available at `http://localhost:9595` with OpenAPI documentation at `http://localhost:9595/docs`.- [Complete the Quick Start Tutorial](quick-start-tutorial.md)

- [Explore Features](features/)

4. **Verify the `/memories` surface**- [Read the FAQ](faq.md)


   ```bash
   curl -i http://localhost:9595/health
   curl -i -H "Authorization: Bearer local-dev-token" http://localhost:9595/stats
   ```

   Both commands should respond with HTTP `200` once the services have initialised.

5. **Stop the stack**

   ```bash
   docker compose down
   ```

## Optional: Local Python Client

If you prefer a Python REPL over `curl`, you can install the packaged client:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m somafractalmemory.cli --help
```

The CLI uses exactly the same `/memories` primitives as the HTTP API and is covered in the Development Manual.

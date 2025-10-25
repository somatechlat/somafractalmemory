SomaFractalMemory

Quick start (local dev)
- Requirements: Docker, Docker Compose
- Default API port: 9595
- Default dev token: devtoken

Run the stack
- Start services with the core profile:
	- docker compose --profile core up -d

Health check
- http://127.0.0.1:9595/healthz should return 200

Try a request
- POST a memory with the pinned dev token:
	- curl -s -X POST http://127.0.0.1:9595/memories \
		-H 'Authorization: Bearer devtoken' -H 'Content-Type: application/json' \
		-d '{"coord":"1000,1001","payload":{"hello":"world"},"memory_type":"episodic"}'

Stats
- curl -s -H 'Authorization: Bearer devtoken' http://127.0.0.1:9595/stats

Notes
- The docker-compose file pins SOMA_API_TOKEN to "devtoken" for reliable local testing.
- If you change the token, update your client headers accordingly.

Secrets and environments
- See `docs/technical-manual/security-secrets.md` for dev vs prod guidance and how to override with `.env`.
- Use `.env.example` as a starting point. Do not commit real secrets.

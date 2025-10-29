SomaFractalMemory

Quick start (local dev)
- Requirements: Docker, Docker Compose
- Default API port: 9595
- Default dev token: devtoken

⚡ Try it in 30 seconds (macOS zsh)

```zsh
# 1) Set a dev token (local only)
export SOMA_API_TOKEN=devtoken

# 2) Start the full stack (API + Postgres + Redis + Qdrant)
docker compose --profile core up -d

# 3) Health check
curl -fsS http://127.0.0.1:9595/healthz

# 4) Store a memory
curl -s -X POST http://127.0.0.1:9595/memories \
	-H "Authorization: Bearer $SOMA_API_TOKEN" \
	-H 'Content-Type: application/json' \
	-d '{"coord":"0.1,0.2,0.3","payload":{"ok":true},"memory_type":"episodic"}'

# 5) Search
curl -s -X POST http://127.0.0.1:9595/memories/search \
	-H "Authorization: Bearer $SOMA_API_TOKEN" \
	-H 'Content-Type: application/json' \
	-d '{"query":"ok", "top_k": 3}'
```

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


<a id="vibe-coding-rules"></a>

## 🎯 Vibe Coding Rules – Engineering Working Agreement

These are the ground rules for how we build, test, and document this project. They’re direct, practical, and designed to keep quality high and friction low.

### 📋 Core principles

1) NO BULLSHIT
- No lies, no mocks, no placeholders, no fake implementations
- No hype: if something is simple, call it simple; if risky, say why
- Be precise about what works and what might fail

2) CHECK FIRST, CODE SECOND
- Review existing files and architecture before proposing changes
- Ask for file contents if context is missing; never assume

3) NO UNNECESSARY FILES
- Prefer modifying existing files over adding new ones
- Don’t split across multiple files without a good reason

4) REAL IMPLEMENTATIONS ONLY
- No TODO stubs; ship working code with error handling
- Use real data paths; clearly mark test data as test data

5) DOCUMENTATION = TRUTH
- Read the docs first; don’t invent APIs or syntax
- Cite official sources when behavior depends on external libraries

6) COMPLETE CONTEXT REQUIRED
- Don’t modify code without understanding flow and dependencies
- If context is missing, request it before changing anything

7) REAL DATA, REAL SERVERS
- Prefer real services and real data when available
- Verify structures and responses; don’t guess

### 🔍 Workflow for every task

1) Understand: read the request; ask up to 2–3 clarifying questions together if needed
2) Gather knowledge: read relevant docs; verify APIs and data formats
3) Investigate: inspect existing files and architecture; trace the flow end-to-end
4) Verify context: confirm what calls what; identify dependencies and impacts
5) Plan: state exactly which files will change and why; note risks/dependencies
6) Implement: write complete, working code based on verified sources
7) Verify: think through edge cases; validate against real services when possible

### 📚 Documentation rules

- Always read official documentation before coding
- Base behavior on real, verified information; include links when relevant
- If docs aren’t accessible, say so—don’t guess

### 🔄 Context & flow rules

- Understand where data comes from and where it goes
- Know which components call and are called by the code you touch
- If any link in the chain is unclear, pause and get the missing context

### 🌐 Real data & servers

- Use real endpoints and datasets when available
- Confirm shapes and error modes from actual responses/logs

### 🗣️ Communication style

- Straight, clear, and concise; no overselling
- Be explicit about limitations, risks, and trade-offs
- Reference sources: “According to the docs at <URL> …”

### ✅ The contract

- Check existing code first; document decisions
- Read documentation proactively and cite it
- Request missing context before modifying code
- Implement real, production-ready solutions
- Verify with real data/services when possible
- Be honest about complexity and outcomes

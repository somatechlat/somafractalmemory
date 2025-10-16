---
title: "Development Setup Checklist"
purpose: "Quick verification checklist for new environment setup"
audience: "New Team Members, Contractors"
last_updated: "2025-10-16"
---

# Development Setup Checklist

## Prerequisites
- [ ] Git installed and configured
- [ ] GitHub SSH key setup
- [ ] Python 3.10+ installed
- [ ] Docker Desktop installed (for Docker Compose)
- [ ] kubectl installed (for Kubernetes)

## Repository Setup
- [ ] Repository cloned: `git clone https://github.com/somatechlat/somafractalmemory.git`
- [ ] Branch switched: `git checkout soma_integration`
- [ ] Remote verified: `git remote -v` shows `origin`

## Local Environment
- [ ] Python virtual environment created: `python -m venv .venv`
- [ ] Virtual environment activated: `source .venv/bin/activate`
- [ ] Dependencies installed: `pip install -r api-requirements.txt`
- [ ] Pre-commit hooks installed: `pre-commit install`

## Configuration
- [ ] `.env` file created from `.env.example` (if applicable)
- [ ] Configuration file reviewed: `config.yaml`
- [ ] API token set (for testing): `export SOMA_API_TOKEN=devtoken`

## Docker Compose (Development)
- [ ] Docker service running
- [ ] Services start successfully: `docker compose up -d`
- [ ] All services healthy: `docker compose ps` shows "healthy"
- [ ] API responds: `curl http://localhost:9595/health` returns 200

## Testing
- [ ] Unit tests run: `pytest tests/`
- [ ] All tests pass (or expected failures documented)
- [ ] Test coverage acceptable (target: >80%)

## Verification Commands
```bash
# Verify Python environment
python --version  # Should be 3.10+

# Verify Git setup
git log --oneline -1  # Should show latest commit

# Verify Docker
docker ps  # Should show running containers

# Verify API
curl http://localhost:9595/health  # Should return {"status": "healthy"}
```

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Port 9595 already in use | Change with `export API_PORT=XXXX` |
| Docker service won't start | Check Docker Desktop is running |
| Tests fail with import errors | Verify venv activated and dependencies installed |
| Pre-commit hook fails | Run `pre-commit run --all-files` to see issues |

## Next Steps
- [ ] Review [Coding Standards](../../development-manual/coding-standards.md)
- [ ] Pick a [starter issue](https://github.com/somatechlat/somafractalmemory/labels/good-first-issue)
- [ ] Read [First Contribution Guide](../first-contribution.md)
- [ ] Join team Slack channel

---

**Setup Complete!** You're ready to start development. 🎉

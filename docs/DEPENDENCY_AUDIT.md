# Dependency Freshness Audit (M20)

**Date**: 2026-10-11
**Auditor**: Claude Opus 4.6 (automated)
**Scope**: Python backend (`backend/requirements.txt`, `backend/pyproject.toml`)

---

## Critical: Security Vulnerabilities (CVEs)

### LangChain Ecosystem — 5 CVEs, fixes require 1.x migration

All CVE fixes are in the langchain 1.x line. No patched 0.3.x versions exist.

| Package | Installed | CVE | Type | Fix Version |
|---|---|---|---|---|
| langchain | 0.3.30 | CVE-2026-55443 | Path traversal | 1.3.9 |
| langchain-core | 0.3.86 | CVE-2026-34070 | Path traversal | 1.2.22 |
| langchain-core | 0.3.86 | CVE-2026-26013 | SSRF | 1.2.11 |
| langchain-openai | 0.3.35 | CVE-2026-41488 | SSRF | 1.1.14 |
| langchain-anthropic | 0.3.22 | CVE-2026-55443 | Path traversal | 1.4.6 |
| langchain-text-splitters | 0.3.11 | CVE-2026-41481 | SSRF | 1.1.2 |

**Risk**: Path traversal allows reading arbitrary files; SSRF allows internal network probing.
**Mitigation**: Pin to 0.3.x with upper bounds (done). Plan 1.x upgrade as priority.

### Other CVEs

| Package | Installed | CVE | Fix Version | Status |
|---|---|---|---|---|
| pip | 26.1.1 | CVE-2026-8643, CVE-2026-13346 | 26.2.1 | **Fixed** (upgraded) |
| unstructured | 0.18.32 | CVE-2026-71428 (SSRF) | 0.24.0 | Needs upgrade |
| nltk | 3.10.3 | CVE-2026-81726 (path traversal) | No fix released | Monitor |

---

## Major Version Gaps (2+ majors behind)

| Package | Installed | Latest | Gap | Blocked By |
|---|---|---|---|---|
| openai | 1.109.1 | 3.28.0 | 2 majors | langchain-openai 0.3.x requires openai<2 |
| langchain-google-genai | 2.1.12 | 4.4.1 | 2 majors | Requires langchain-core 1.x |

---

## Major Version Gaps (1 major behind)

| Package | Installed | Latest | Notes |
|---|---|---|---|
| langchain | 0.3.30 | 1.4.4 | Ecosystem-wide 1.x migration needed |
| langchain-core | 0.3.86 | 1.6.9 | Core dependency for all langchain-* |
| langchain-openai | 0.3.35 | 1.7.0 | Unblocks openai 2.x/3.x |
| langchain-anthropic | 0.3.22 | 1.7.5 | Unblocks anthropic 1.x |
| langchain-text-splitters | 0.3.11 | 1.1.3 | |
| anthropic | 0.125.0 | 1.13.0 | Blocked by langchain-anthropic 0.3.x |
| huggingface_hub | 1.33.0 | 2.2.0 | Transitive dep of sentence-transformers |
| pandas | 2.3.3 | 3.0.6 | Only used in load-tests |
| marshmallow | 3.26.2 | 4.3.1 | Transitive dependency |

---

## Deprecated API Usage

### langchain_community Ollama imports (deprecated)

File: `backend/app/services/ragas/service.py`

```python
# Lines 143, 166 — These imports are deprecated in favor of langchain-ollama
from langchain_community.chat_models import ChatOllama      # → langchain_ollama.ChatOllama
from langchain_community.embeddings import OllamaEmbeddings  # → langchain_ollama.OllamaEmbeddings
```

**Action**: Install `langchain-ollama` and update imports. Low risk, isolated to RAGAS service.

---

## Issues Fixed in This Audit

1. **bcrypt 5.0.0 → 4.3.0**: bcrypt 5.0 broke passlib 1.7.4 (removed `__about__` module, changed API). Downgraded to 4.3.0 (latest 4.x). Password hashing now works correctly.
2. **pip 26.1.1 → 26.2.1**: Fixed CVE-2026-8643 (console_scripts path injection) and CVE-2026-13346 (double-encoded URLs).
3. **requirements.txt**: Added `<1.0.0` upper bounds on langchain packages to prevent accidental major upgrades, with CVE annotations.

---

## Recommended Upgrade Plan

### Phase 1: Immediate (low risk)
- [x] Fix bcrypt/passlib incompatibility
- [x] Update pip
- [x] Add upper bounds to langchain pins
- [ ] Update `unstructured` to >=0.24.0 (SSRF fix)

### Phase 2: Short-term (medium risk, 1-2 sprints)
- [ ] **LangChain 1.x migration** — blocks fixing 5 CVEs
  - Upgrade langchain, langchain-core, langchain-openai, langchain-anthropic, langchain-text-splitters together
  - Then unpin openai (→ 3.x) and anthropic (→ 1.x)
  - Test all chat, RAG, agent, and embedding flows
  - Key API changes: message types, tool calling, runnable interface
- [ ] Replace deprecated Ollama imports with `langchain-ollama`
- [ ] Update `langchain-google-genai` 2.x → 4.x

### Phase 3: When convenient (low priority)
- [ ] `pandas` 2.x → 3.x (load-tests only)
- [ ] Monitor nltk CVE-2026-81726 for fix release
- [ ] Evaluate passlib alternatives (e.g., `argon2-cffi`) to remove bcrypt pin

---

## Packages at Latest (no action needed)

These direct dependencies are current:

fastapi 0.143.0, uvicorn 0.54.0, pyjwt 2.15.1, sqlalchemy 2.1.4,
asyncpg 0.32.0, alembic 1.20.0, redis 8.1.0, hiredis 3.4.2,
pydantic 2.14.0, pydantic-settings 2.15.0, httpx 0.28.1,
structlog 26.1.0, tenacity 9.2.1, croniter 6.2.4, pypdf 6.20.0,
beautifulsoup4 4.15.0, lxml 6.1.3, rich 15.0.0, pytest 9.1.1,
ruff 0.17.0, mypy 2.4.0, websockets 17.2, nh3 0.3.7

# Taskpilot Project Context

## Product Direction
Taskpilot is primarily an auto-apply platform.

The intended user journey is:
- upload a resume
- get ATS-style suggestions that improve application quality
- maintain one reusable application profile
- choose target companies or jobs
- let workers apply through company career pages
- track outcomes from one dashboard

Resume analysis is a support feature. The main product is reliable automated job application execution.

## Architecture Snapshot
Taskpilot follows the architecture in [codex.md](/Users/pritpatel/Desktop/taskpilot1/codex.md):
- `frontend/`: React + TypeScript UI only
- `backend/`: FastAPI API with service/repository separation
- `workers/`: async RabbitMQ consumers and processors
- PostgreSQL: source of truth
- RabbitMQ: async workflow, retries, and DLQ handling
- S3-compatible object storage: resume and artifact storage
- Redis: intended for caching and rate limiting
- outbox pattern: reliable DB -> queue publishing

Core rules:
- API stays thin and stateless
- heavy work runs only in workers
- files are stored in object storage, not locally
- correctness and durability come before convenience

## What Exists Today
- Upload flow:
  - presign endpoint
  - direct object-storage upload
  - application creation after upload
- Durable backend workflow:
  - PostgreSQL writes
  - outbox publisher
  - RabbitMQ queues
  - retry and DLQ handling
- Worker stages currently implemented:
  - application processing
  - resume processing
  - scoring
  - stuck-job recovery
- Persistent DB state for applications and scores
- Frontend upload page that:
  - uploads a file
  - creates an application
  - polls for status
  - shows score and breakdown when available
- Metrics and tracing are partially wired in backend and workers

Current implemented lifecycle:
`queued -> processing -> resume_processed -> completed`

Current implemented pipeline:
`upload -> application -> resume processing -> scoring -> result polling`

## Planned User-Facing Features
### V1 Priorities
- one-time reusable application profile
- company / job target lists
- approval mode before submit
- application evidence and proof of submission
- application tracking timeline
- duplicate-apply protection

### Support Features
- ATS-style suggestions before apply
- profile completeness guidance
- failure recovery visibility

### Later Roadmap
- site-specific success analytics
- quotas and daily goals
- richer automation controls and preferences

## Highest-Value Work Remaining
- durable user profile domain for reusable application answers
- target-selection flow for companies and jobs
- auto-apply request and execution worker for company career pages
- browser automation reliability, evidence capture, and outcome tracking
- real auth and production hardening
- Redis-backed rate limiting and caching
- stronger test coverage and operational observability

## Bottom Line
Taskpilot already has a real async backbone: upload, DB writes, outbox, queues, workers, scoring, and polling UI.

The next major milestone is production-grade auto-apply readiness:
- reusable profile
- target selection
- worker-only career-page automation
- durable tracking and proof of what happened

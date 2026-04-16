# Taskpilot

Purpose:

* `frontend/` contains the React + TypeScript UI only.
* `backend/` contains the FastAPI API, split into routes, services, repositories, models, schemas, core, middleware, and observability.
* `workers/` contains RabbitMQ consumers and async job processors only.
* `shared/` contains contracts only: queue schemas, API contracts, enums, and constants.
* `infra/` contains Docker, Compose, deployment, monitoring, and RabbitMQ infrastructure files.

Rules:

* No business logic in `frontend/`.
* No HTTP logic in `workers/`.
* No database access outside `backend/app/repositories/`.
* No runtime coupling through `shared/`; it is contracts-only.
* Legacy TypeScript serverless artifacts are isolated under `backend/legacy/` and are not part of the target production runtime.

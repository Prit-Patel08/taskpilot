# Job Discovery

Job discovery is backend-driven.

Frontend responsibilities:

* collect filters
* call backend APIs through `src/services/api.ts`
* render paginated results and metrics

Backend responsibilities:

* search jobs
* return company filter options
* return ingestion metrics
* own all database access

Current placeholder API contracts:

* `GET /v1/jobs/search`
* `GET /v1/jobs/companies`
* `GET /v1/metrics/ingestion`

Legacy serverless and direct-database shortcut code has been removed from the frontend flow.

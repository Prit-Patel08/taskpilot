export const config = {
  db: {
    connectionString: process.env.DATABASE_URL!,
  },
  ingestion: {
    companyConcurrency: parseInt(
      process.env.JOB_INGEST_COMPANY_CONCURRENCY ?? "10",
      10,
    ),
    companyPageSize: parseInt(
      process.env.JOB_INGEST_COMPANY_PAGE_SIZE ?? "500",
      10,
    ),
    maxJobsPerCompany: parseInt(
      process.env.JOB_INGEST_MAX_JOBS_PER_COMPANY ?? "2000",
      10,
    ),
    perCompanyDelayMs: parseInt(
      process.env.JOB_INGEST_PER_COMPANY_DELAY_MS ?? "250",
      10,
    ),
  },
};

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
    schedulerCron: process.env.JOB_INGEST_SCHEDULE_CRON ?? "*/5 * * * *",
    queueEnqueueLimit: parseInt(
      process.env.JOB_INGEST_QUEUE_ENQUEUE_LIMIT ?? "500",
      10,
    ),
    queueBatchSize: parseInt(
      process.env.JOB_INGEST_QUEUE_BATCH_SIZE ?? "50",
      10,
    ),
    queuePollIntervalMs: parseInt(
      process.env.JOB_INGEST_QUEUE_POLL_INTERVAL_MS ?? "5000",
      10,
    ),
    queueWorkerConcurrency: parseInt(
      process.env.JOB_INGEST_QUEUE_WORKER_CONCURRENCY ?? "5",
      10,
    ),
    queueMaxAttempts: parseInt(
      process.env.JOB_INGEST_QUEUE_MAX_ATTEMPTS ?? "5",
      10,
    ),
    queueRetryDelayMs: parseInt(
      process.env.JOB_INGEST_QUEUE_RETRY_DELAY_MS ?? "60000",
      10,
    ),
    queueClaimTimeoutMs: parseInt(
      process.env.JOB_INGEST_QUEUE_CLAIM_TIMEOUT_MS ?? "300000",
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
    atsRateLimits: {
      greenhouse: parseInt(process.env.JOB_INGEST_RATE_GREENHOUSE_MS ?? "250", 10),
      lever: parseInt(process.env.JOB_INGEST_RATE_LEVER_MS ?? "250", 10),
      ashby: parseInt(process.env.JOB_INGEST_RATE_ASHBY_MS ?? "250", 10),
      workday: parseInt(process.env.JOB_INGEST_RATE_WORKDAY_MS ?? "500", 10),
    },
    shardTotal: parseInt(process.env.INGESTION_SHARD_TOTAL ?? "1", 10),
    shardIndex: parseInt(process.env.INGESTION_SHARD_INDEX ?? "0", 10),
  },
  ranking: {
    schedulerCron: process.env.JOB_RANK_SCHEDULE_CRON ?? "*/30 * * * *",
    limit: parseInt(process.env.JOB_RANK_LIMIT ?? "5000", 10),
    preferredLocation: process.env.JOB_RANK_PREFERRED_LOCATION ?? "",
    remotePreference: process.env.JOB_RANK_REMOTE_PREFERENCE ?? "",
    skillKeywords: (process.env.JOB_RANK_SKILLS ?? "")
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean),
  },
  monitoring: {
    metricsCron: process.env.MONITORING_METRICS_CRON ?? "*/15 * * * *",
    alertsCron: process.env.MONITORING_ALERTS_CRON ?? "*/5 * * * *",
    alertFailureRate: parseFloat(
      process.env.MONITORING_ALERT_FAILURE_RATE ?? "0.3",
    ),
    alertQueueDepth: parseInt(
      process.env.MONITORING_ALERT_QUEUE_DEPTH ?? "500",
      10,
    ),
    alertWebhookUrl: process.env.MONITORING_WEBHOOK_URL ?? "",
  },
};

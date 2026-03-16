import { randomUUID } from "crypto";
import { pathToFileURL } from "url";
import pLimit from "p-limit";
import { config } from "../config";
import { log } from "../logger";
import { getCompaniesByIds } from "./companyRepository";
import { ingestCompany } from "./jobIngestionWorker";
import { startIngestionRun, finishIngestionRun } from "./ingestionRunRepository";
import { claimQueueBatch, markQueueFailure, markQueueSuccess } from "./queueRepository";
import { nextRetryDelay } from "./retryPolicy";
import type { Company, QueueTask } from "./types";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function processTask(task: QueueTask, company: Company | undefined) {
  if (!company) {
    log.warn("Queue task company not found", { queueId: task.id, companyId: task.company_id });
    await markQueueFailure(
      task.id,
      "Company not found",
      nextRetryDelay(task.attempts),
      task.attempts,
      config.ingestion.queueMaxAttempts,
    );
    return;
  }

  const runId = await startIngestionRun(company.id, company.ats_type, task.id);

  try {
    const result = await ingestCompany(company);
    await markQueueSuccess(task.id);
    await finishIngestionRun(
      runId,
      "success",
      result.inserted,
      result.skipped,
      result.duplicates,
    );
    log.info("Queue task processed", {
      queueId: task.id,
      companyId: company.id,
      inserted: result.inserted,
      skipped: result.skipped,
      duplicates: result.duplicates,
    });
  } catch (err) {
    const errorMessage = (err as Error).message;
    const status = await markQueueFailure(
      task.id,
      errorMessage,
      nextRetryDelay(task.attempts),
      task.attempts,
      config.ingestion.queueMaxAttempts,
    );
    await finishIngestionRun(runId, "failed", 0, 0, 0, errorMessage);
    log.error("Queue task failed", {
      queueId: task.id,
      companyId: company.id,
      status,
      error: errorMessage,
    });
  }
}

export async function startIngestionWorker(): Promise<void> {
  const workerId = process.env.INGESTION_WORKER_ID ?? randomUUID();
  log.info("Ingestion worker started", {
    workerId,
    shardIndex: config.ingestion.shardIndex,
    shardTotal: config.ingestion.shardTotal,
  });

  while (true) {
    const tasks = await claimQueueBatch(
      config.ingestion.queueBatchSize,
      workerId,
      config.ingestion.queueClaimTimeoutMs,
      config.ingestion.shardTotal,
      config.ingestion.shardIndex,
    );

    if (!tasks.length) {
      await sleep(config.ingestion.queuePollIntervalMs);
      continue;
    }

    const companies = await getCompaniesByIds(tasks.map((task) => task.company_id));
    const companyMap = new Map(companies.map((company) => [company.id, company]));

    const limit = pLimit(config.ingestion.queueWorkerConcurrency);
    await Promise.all(
      tasks.map((task) =>
        limit(() => processTask(task, companyMap.get(task.company_id))),
      ),
    );
  }
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  startIngestionWorker().catch((err) => {
    log.error("Ingestion worker crashed", { error: (err as Error).message });
    process.exit(1);
  });
}

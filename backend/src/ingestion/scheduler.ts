import cron from "node-cron";
import { pathToFileURL } from "url";
import { log } from "../logger";
import { config } from "../config";
import { enqueueDueCompanies } from "./queueRepository";

export function startIngestionScheduler() {
  const cronExpr = config.ingestion.schedulerCron;

  const enqueueNow = async () => {
    log.info("Enqueuing due companies");
    try {
      const enqueued = await enqueueDueCompanies(
        config.ingestion.queueEnqueueLimit,
      );
      log.info("Enqueued companies", { count: enqueued });
    } catch (err) {
      log.error("Scheduler enqueue failed", {
        error: (err as Error).message,
      });
    }
  };

  enqueueNow();
  cron.schedule(cronExpr, enqueueNow);

  log.info("Ingestion scheduler started", { cron: cronExpr });
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  startIngestionScheduler();
}

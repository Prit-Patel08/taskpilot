import cron from "node-cron";
import { runJobIngestionOnce } from "./jobIngestionWorker";
import { log } from "../logger";

export function startJobIngestionScheduler() {
  cron.schedule("*/15 * * * *", async () => {
    log.info("Starting scheduled job ingestion run");
    try {
      await runJobIngestionOnce();
    } catch (err) {
      log.error("Scheduled job ingestion failed", {
        error: (err as Error).message,
      });
    }
  });

  log.info("Job ingestion scheduler started (every 15 minutes)");
}

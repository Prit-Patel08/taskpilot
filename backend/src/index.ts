import { startIngestionScheduler } from "./ingestion/scheduler";
import { startIngestionWorker } from "./ingestion/worker";
import { startRankingScheduler } from "./ranking/rankingScheduler";
import { startMonitoringScheduler } from "./monitoring/monitoringScheduler";
import { log } from "./logger";

async function main() {
  const role = process.env.INGESTION_ROLE ?? "all";

  if (role === "scheduler" || role === "all") {
    startIngestionScheduler();
  }

  if (role === "worker" || role === "all") {
    startIngestionWorker().catch((err) => {
      log.error("Ingestion worker failed to start", {
        error: (err as Error).message,
      });
    });
  }

  if (role === "ranking" || role === "all") {
    startRankingScheduler();
  }

  if (role === "monitoring" || role === "all") {
    startMonitoringScheduler();
  }

  log.info("Service started", { role });
}

main().catch((err) => {
  log.error("Fatal error starting service", {
    error: (err as Error).message,
  });
  process.exit(1);
});

import { startJobIngestionScheduler } from "./jobs/scheduler";
import { log } from "./logger";

async function main() {
  startJobIngestionScheduler();
  log.info("Service started");
}

main().catch((err) => {
  log.error("Fatal error starting service", {
    error: (err as Error).message,
  });
  process.exit(1);
});

import { pathToFileURL } from "url";
import { log } from "../logger";
import { startIngestionWorker } from "./worker";

async function superviseWorker() {
  const maxRestarts = parseInt(process.env.INGESTION_WORKER_RESTARTS ?? "5", 10);
  const backoffMs = parseInt(process.env.INGESTION_WORKER_RESTART_DELAY_MS ?? "5000", 10);
  const shardIndex = process.env.INGESTION_SHARD_INDEX ?? "0";
  const shardTotal = process.env.INGESTION_SHARD_TOTAL ?? "1";

  let attempts = 0;
  while (attempts <= maxRestarts) {
    try {
      await startIngestionWorker();
      return;
    } catch (err) {
      attempts += 1;
      log.error("Worker crashed", {
        attempt: attempts,
        error: (err as Error).message,
        shardIndex,
        shardTotal,
      });
      if (attempts > maxRestarts) {
        process.exit(1);
      }
      await new Promise((resolve) => setTimeout(resolve, backoffMs * attempts));
    }
  }
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  superviseWorker().catch((err) => {
    log.error("Worker supervisor failed", { error: (err as Error).message });
    process.exit(1);
  });
}

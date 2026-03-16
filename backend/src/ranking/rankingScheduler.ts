import cron from "node-cron";
import { pathToFileURL } from "url";
import { config } from "../config";
import { log } from "../logger";
import { rankRecentJobs } from "./rankingWorker";

function buildRankContext() {
  const preferredLocation = config.ranking.preferredLocation.trim() || undefined;
  const remotePreference = config.ranking.remotePreference.trim();
  const remote =
    remotePreference === "remote" ||
    remotePreference === "hybrid" ||
    remotePreference === "onsite"
      ? remotePreference
      : undefined;
  return {
    preferredLocation,
    remotePreference: remote,
    skillKeywords: config.ranking.skillKeywords,
  };
}

export function startRankingScheduler() {
  const cronExpr = config.ranking.schedulerCron;

  const runOnce = async () => {
    try {
      const context = buildRankContext();
      const count = await rankRecentJobs(context, config.ranking.limit);
      log.info("Ranking run complete", { count });
    } catch (err) {
      log.error("Ranking run failed", { error: (err as Error).message });
    }
  };

  runOnce();
  cron.schedule(cronExpr, runOnce);
  log.info("Ranking scheduler started", { cron: cronExpr });
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  startRankingScheduler();
}

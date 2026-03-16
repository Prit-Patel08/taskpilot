import cron from "node-cron";
import { pathToFileURL } from "url";
import { config } from "../config";
import { log } from "../logger";
import { runMetricsRollup } from "./metricsWorker";
import { runAlertsOnce } from "./alertsWorker";

export function startMonitoringScheduler() {
  cron.schedule(config.monitoring.metricsCron, async () => {
    try {
      await runMetricsRollup();
    } catch (err) {
      log.error("Metrics scheduler failed", { error: (err as Error).message });
    }
  });

  cron.schedule(config.monitoring.alertsCron, async () => {
    try {
      await runAlertsOnce();
    } catch (err) {
      log.error("Alerts scheduler failed", { error: (err as Error).message });
    }
  });

  log.info("Monitoring scheduler started", {
    metricsCron: config.monitoring.metricsCron,
    alertsCron: config.monitoring.alertsCron,
  });
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  startMonitoringScheduler();
}

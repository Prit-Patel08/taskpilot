import { pathToFileURL } from "url";
import { config } from "../config";
import { log } from "../logger";
import { getFailureRate, getQueueDepth } from "./metricsRepository";

async function sendWebhook(message: string) {
  if (!config.monitoring.alertWebhookUrl) return;
  try {
    await fetch(config.monitoring.alertWebhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: message }),
    });
  } catch (err) {
    log.warn("Alert webhook failed", {
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

export async function runAlertsOnce(): Promise<void> {
  const [queueDepth, failureRate] = await Promise.all([
    getQueueDepth(),
    getFailureRate(60),
  ]);

  if (queueDepth > config.monitoring.alertQueueDepth) {
    const message = `TaskPilot alert: queue depth ${queueDepth} exceeds threshold ${config.monitoring.alertQueueDepth}`;
    log.warn(message);
    await sendWebhook(message);
  }

  if (failureRate > config.monitoring.alertFailureRate) {
    const message = `TaskPilot alert: failure rate ${(failureRate * 100).toFixed(
      1,
    )}% exceeds threshold ${(config.monitoring.alertFailureRate * 100).toFixed(1)}%`;
    log.warn(message);
    await sendWebhook(message);
  }
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  runAlertsOnce().catch((err) => {
    log.error("Alerts run failed", { error: (err as Error).message });
    process.exit(1);
  });
}

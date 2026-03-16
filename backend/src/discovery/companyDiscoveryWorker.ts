import { config } from "../config";
import { log } from "../logger";
import { discoverCompanyCandidates } from "./discoverCompanyCandidates";
import {
  autoPromoteTopCandidates,
  upsertCompanyCandidate,
} from "./companyDiscoveryRepository";
import { importSeedDomains } from "./seedImporter";

function parseSeedDomains(): string[] {
  const raw = process.env.COMPANY_DISCOVERY_SEEDS ?? "";
  return raw
    .split(",")
    .map((domain) => domain.trim())
    .filter(Boolean);
}

export async function runCompanyDiscoveryOnce(): Promise<void> {
  const seeds = parseSeedDomains();
  if (!seeds.length) {
    log.warn("No COMPANY_DISCOVERY_SEEDS provided. Exiting discovery.");
    return;
  }

  log.info("Starting company discovery", { seeds: seeds.length });

  const seedInserted = await importSeedDomains(seeds);
  log.info("Seed domains imported", { inserted: seedInserted });

  for (const domain of seeds) {
    try {
      const candidates = await discoverCompanyCandidates(domain);
      for (const candidate of candidates) {
        await upsertCompanyCandidate(candidate);
      }
      log.info("Discovery complete for domain", {
        domain,
        candidates: candidates.length,
      });
    } catch (err) {
      log.error("Discovery failed for domain", {
        domain,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }

  log.info("Company discovery run complete");

  const promoted = await autoPromoteTopCandidates();
  log.info("Auto-promoted candidates", { promoted });
}

if (config.ingestion) {
  runCompanyDiscoveryOnce().catch((err) => {
    log.error("Company discovery failed", {
      error: err instanceof Error ? err.message : String(err),
    });
    process.exit(1);
  });
}

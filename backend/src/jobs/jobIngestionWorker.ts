import type { Company, RawJob } from "./types";
import { getCompaniesPage, updateCompanyLastCrawled } from "./companyRepository";
import { fetchGreenhouseJobs } from "./fetchers/greenhouse";
import { fetchLeverJobs } from "./fetchers/lever";
import { fetchAshbyJobs } from "./fetchers/ashby";
import { normalizeJob } from "./jobNormalizer";
import { upsertJobs } from "./jobRepository";
import { config } from "../config";
import { log } from "../logger";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchCompanyJobs(company: Company) {
  try {
    let rawJobs: RawJob[] = [];

    switch (company.ats_type) {
      case "greenhouse":
        rawJobs = await fetchGreenhouseJobs(company);
        break;
      case "lever":
        rawJobs = await fetchLeverJobs(company);
        break;
      case "ashby":
        rawJobs = await fetchAshbyJobs(company);
        break;
      case "workday":
      case "custom":
      default:
        log.info("ATS type not yet implemented; skipping", {
          companyId: company.id,
          ats_type: company.ats_type,
        });
        return;
    }

    if (!rawJobs.length) {
      log.info("No jobs returned from ATS", { companyId: company.id });
      await updateCompanyLastCrawled(company.id);
      return;
    }

    const normalized = rawJobs.map((raw) => normalizeJob(company, raw));
    const { inserted, skipped } = await upsertJobs(normalized);

    log.info("Upserted jobs", {
      companyId: company.id,
      totalRaw: rawJobs.length,
      inserted,
      skipped,
    });

    await updateCompanyLastCrawled(company.id);
  } catch (err) {
    log.error("Failed to ingest company jobs", {
      companyId: company.id,
      error: (err as Error).message,
    });
  } finally {
    if (config.ingestion.perCompanyDelayMs > 0) {
      await sleep(config.ingestion.perCompanyDelayMs);
    }
  }
}

export async function runJobIngestionOnce(): Promise<void> {
  const { companyConcurrency, companyPageSize } = config.ingestion;
  let offset = 0;

  while (true) {
    const companies = await getCompaniesPage(offset);
    if (!companies.length) break;

    log.info("Processing company page", { offset, count: companies.length });

    for (let i = 0; i < companies.length; i += companyConcurrency) {
      const batch = companies.slice(i, i + companyConcurrency);
      await Promise.all(batch.map((company) => fetchCompanyJobs(company)));
    }

    offset += companyPageSize;
  }

  log.info("Job ingestion run complete");
}

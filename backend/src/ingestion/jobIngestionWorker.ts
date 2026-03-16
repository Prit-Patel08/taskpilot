import type { Company, IngestionResult, RawJob } from "./types";
import { getCompaniesPage, updateCompanyLastCrawled } from "./companyRepository";
import { fetchGreenhouseJobs } from "./fetchers/greenhouse";
import { fetchLeverJobs } from "./fetchers/lever";
import { fetchAshbyJobs } from "./fetchers/ashby";
import { fetchWorkdayJobs } from "./fetchers/workday";
import { normalizeJob } from "./jobNormalizer";
import { upsertJobs } from "./jobRepository";
import { dedupeJobs } from "./jobDeduplicator";
import { findDedupeCandidates, linkJobSource } from "./dedupeRepository";
import { config } from "../config";
import { log } from "../logger";
import pLimit from "p-limit";
import { pathToFileURL } from "url";
import { configureRateLimit, waitForRateLimit } from "./rateLimiter";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function ingestCompany(company: Company): Promise<IngestionResult> {
  try {
    let rawJobs: RawJob[] = [];

    const rateLimitMs = config.ingestion.atsRateLimits[company.ats_type] ?? 250;
    configureRateLimit(company.ats_type, rateLimitMs);
    await waitForRateLimit(company.ats_type);

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
        rawJobs = await fetchWorkdayJobs(company);
        break;
      case "custom":
      default:
        log.info("ATS type not yet implemented; skipping", {
          companyId: company.id,
          ats_type: company.ats_type,
        });
        return {
          companyId: company.id,
          totalRaw: 0,
          inserted: 0,
          skipped: 0,
          duplicates: 0,
        };
    }

    if (!rawJobs.length) {
      log.info("No jobs returned from ATS", { companyId: company.id });
      await updateCompanyLastCrawled(company.id);
      return {
        companyId: company.id,
        totalRaw: 0,
        inserted: 0,
        skipped: 0,
        duplicates: 0,
      };
    }

    const normalized = rawJobs.map((raw) => normalizeJob(company, raw));
    const { deduped, duplicates } = dedupeJobs(normalized);
    const { inserted, skipped } = await upsertJobs(deduped);

    log.info("Upserted jobs", {
      companyId: company.id,
      totalRaw: rawJobs.length,
      inserted,
      skipped,
      duplicates,
    });

    const normalizedPairs = normalized.map((job, idx) => ({
      job,
      raw: rawJobs[idx],
    }));
    await Promise.all(
      normalizedPairs.map(async ({ job, raw }) => {
        try {
          const candidates = await findDedupeCandidates(
            company.id,
            job.hash,
            raw.applyUrl ?? null,
            raw.externalId ?? null,
            raw.source ?? null,
          );
          const match = candidates[0];
          if (match) {
            await linkJobSource(
              match.id,
              raw.source ?? job.source,
              raw.externalId ?? job.externalId ?? null,
              raw.rawPayload ?? null,
            );
          }
        } catch (err) {
          log.warn("Failed to link job source", {
            companyId: company.id,
            error: (err as Error).message,
          });
        }
      }),
    );

    await updateCompanyLastCrawled(company.id);

    return {
      companyId: company.id,
      totalRaw: rawJobs.length,
      inserted,
      skipped,
      duplicates,
    };
  } catch (err) {
    log.error("Failed to ingest company jobs", {
      companyId: company.id,
      error: (err as Error).message,
    });
    throw err;
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

    const limit = pLimit(companyConcurrency);
    await Promise.all(
      companies.map((company) =>
        limit(async () => {
          try {
            await ingestCompany(company);
          } catch {
            // Errors are already logged inside ingestCompany.
          }
        }),
      ),
    );

    offset += companyPageSize;
  }

  log.info("Job ingestion run complete");
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  runJobIngestionOnce().catch((err) => {
    log.error("Job ingestion run failed", {
      error: (err as Error).message,
    });
    process.exit(1);
  });
}

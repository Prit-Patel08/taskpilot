type RankSignals = {
  postedAt?: Date | null;
  companyScore?: number | null;
  locationMatch?: number | null;
  remoteMatch?: number | null;
  skillMatch?: number | null;
};

type RankWeights = {
  recency: number;
  company: number;
  location: number;
  remote: number;
  skill: number;
};

const DEFAULT_WEIGHTS: RankWeights = {
  recency: 0.35,
  company: 0.2,
  location: 0.2,
  remote: 0.15,
  skill: 0.1,
};

const DEFAULT_RECENCY_HALF_LIFE_DAYS = 7;

export function recencyScore(
  postedAt: Date | null | undefined,
  now = new Date(),
  halfLifeDays = DEFAULT_RECENCY_HALF_LIFE_DAYS,
): number {
  if (!postedAt) return 0;
  const ageMs = Math.max(0, now.getTime() - postedAt.getTime());
  const halfLifeMs = halfLifeDays * 24 * 60 * 60 * 1000;
  return Math.exp(-Math.log(2) * (ageMs / halfLifeMs));
}

function clamp(value: number | null | undefined, min = 0, max = 1): number {
  if (value === null || value === undefined || Number.isNaN(value)) return 0;
  return Math.min(max, Math.max(min, value));
}

export function rankJob(
  signals: RankSignals,
  weights: RankWeights = DEFAULT_WEIGHTS,
  now = new Date(),
): number {
  const recency = recencyScore(signals.postedAt ?? null, now);
  const company = clamp(signals.companyScore);
  const location = clamp(signals.locationMatch);
  const remote = clamp(signals.remoteMatch);
  const skill = clamp(signals.skillMatch);

  return (
    weights.recency * recency +
    weights.company * company +
    weights.location * location +
    weights.remote * remote +
    weights.skill * skill
  );
}

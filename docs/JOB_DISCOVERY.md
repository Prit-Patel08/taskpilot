# Job Discovery (Greenhouse API) – Implementation Guide

This project uses **Vite + React** (not Next.js). Job fetching runs in a **Vercel serverless API**; the Jobs page reads from Supabase.

---

## STEP 1 – Supabase database

### What to do

Create a `jobs` table that stores job listings from Greenhouse (and optionally other sources later).

### Where to run the SQL

1. Open **Supabase Dashboard** → **SQL Editor**.
2. Click **New query**.
3. Paste the SQL below and click **Run**.

### SQL

```sql
-- Jobs from Greenhouse (and other sources later)
create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  external_id text not null,
  source text not null default 'greenhouse',
  company text not null,
  title text not null,
  location text,
  description text,
  apply_url text not null,
  created_at timestamptz not null default now(),
  unique(external_id, source)
);

-- Allow anyone to read jobs (dashboard is behind auth; optionally restrict later)
alter table public.jobs enable row level security;

create policy "Anyone can read jobs"
  on public.jobs for select
  using (true);

-- Only server/service can insert (API uses service role key)
create policy "Service can insert jobs"
  on public.jobs for insert
  with check (true);

create policy "Service can update jobs"
  on public.jobs for update
  using (true)
  with check (true);
```

**Notes:**

- `external_id` = Greenhouse job id (e.g. `7546284`). With `unique(external_id, source)` we avoid duplicate rows when re-fetching.
- `source` = `'greenhouse'` so you can add other ATS sources later.
- RLS: reads allowed for all (your app is behind auth); insert/update intended for the serverless API using the **Supabase service role key**.

---

## STEP 2 – Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│ Greenhouse API  │────▶│ Vercel API           │────▶│ Supabase        │
│ /boards/{co}/   │     │ /api/fetch-jobs      │     │ public.jobs     │
│ jobs            │     │ (parse & upsert)     │     │                 │
└─────────────────┘     └──────────────────────┘     └────────┬────────┘
                                                             │
┌─────────────────┐     ┌──────────────────────┐             │
│ Jobs page       │────▶│ Supabase client      │◀────────────┘
│ /app/jobs       │     │ .from('jobs').select │
└─────────────────┘     └──────────────────────┘
```

1. **Trigger:** You (or a cron) call `GET /api/fetch-jobs?companies=stripe,vercel`.
2. **API:** Fetches each company’s jobs from Greenhouse, maps to table columns, upserts into `public.jobs` (on conflict do update or skip).
3. **Jobs page:** Loads jobs from Supabase and displays Company, Role, Location, Apply Link.

---

## STEP 3 – Greenhouse API format

### Endpoint

```
GET https://boards-api.greenhouse.io/v1/boards/{company}/jobs
```

Examples:

- `https://boards-api.greenhouse.io/v1/boards/stripe/jobs`
- `https://boards-api.greenhouse.io/v1/boards/vercel/jobs`

No API key required for the public job board API.

### Response shape (relevant fields)

- `jobs`: array of job objects.
- Each job:
  - `id` (number) → store as `external_id` (e.g. `"7546284"`).
  - `title` (string) → `title`.
  - `company_name` (string) → `company`.
  - `location.name` (string) → `location`.
  - `absolute_url` (string) → `apply_url`.
- We do **not** get full `description` from the list endpoint; you can leave `description` null or add a later step that calls the job-detail endpoint per job.

---

## STEP 4 – Files to create or modify

| File | Purpose |
|------|--------|
| `lib/jobFetcher.ts` | Fetch from Greenhouse, map to DB rows, upsert into Supabase (used by API). |
| `api/fetch-jobs.ts` | Vercel serverless handler: read `companies` from query, call job fetcher, return counts/errors. |
| `src/lib/jobsDb.ts` | Client-side: fetch jobs from Supabase for the Jobs page. |
| `src/pages/dashboard/Jobs.tsx` | Load jobs from Supabase; display Company, Role, Location, Apply Link (and optional description). |

No Next.js App Router; the app is Vite and the only “backend” is the Vercel API.

---

## STEP 5 – Job fetching script

**File: `lib/jobFetcher.ts`**

- **What it does:** Calls the Greenhouse API for each company slug, parses `jobs[]`, maps each job to a row (`external_id`, `source`, `company`, `title`, `location`, `description`, `apply_url`), and **upserts** into `public.jobs` with `onConflict: "external_id,source"` so the same Greenhouse job is not duplicated.
- **Where it runs:** Only in the Vercel serverless function (Node). It receives an existing Supabase client (created with the **service role** key in the API).

---

## STEP 6 – API route (Vercel)

**File: `api/fetch-jobs.ts`**

- **What it does:** Handles `GET /api/fetch-jobs`. Reads `companies` from the query (e.g. `?companies=stripe,vercel`), creates a Supabase client with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, calls `fetchGreenhouseJobs(supabase, companies)`, and returns JSON with `ok`, `inserted`, `errors`.
- **Where to run it:** Deploy to Vercel; the route is available at `https://<your-app>.vercel.app/api/fetch-jobs`. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in Vercel → Project → Environment Variables.

---

## STEP 7 – Jobs page and DB

**Files: `src/lib/jobsDb.ts`, `src/pages/dashboard/Jobs.tsx`**

- **jobsDb.ts:** Exposes `getJobs()` which selects from `public.jobs` ordered by `created_at` desc. Used by the Jobs page.
- **Jobs.tsx:** On mount calls `getJobs()`, shows loading and error states, and renders a card per job with **Company**, **Role** (title), **Location**, and **Apply** link (opens `apply_url` in a new tab). “Refresh” re-fetches from Supabase.

---

## STEP 8 – Protections

- **Duplicate jobs:** Prevented by `unique(external_id, source)` and upsert in `jobFetcher.ts` (`onConflict: "external_id,source"`).
- **API errors:** Greenhouse fetch failures (non-OK status or throw) are pushed to an `errors` array and returned in the JSON; the API still returns 200 so you can see which companies failed.
- **Logging:** The API route logs to the server console on 500 (e.g. `console.error("fetch-jobs error:", message)`). In Vercel, view logs in the project’s Functions tab or in the deployment logs.

---

## STEP 9 – How to test (companies)

Use the `companies` query param when calling the API:

- **Stripe:** `.../api/fetch-jobs?companies=stripe`
- **Notion:** `.../api/fetch-jobs?companies=notion`
- **Vercel:** `.../api/fetch-jobs?companies=vercel`
- **Cloudflare:** `.../api/fetch-jobs?companies=cloudflare`
- **Multiple:** `.../api/fetch-jobs?companies=stripe,vercel,notion`

Then open the Jobs page in the app; it should list jobs from `public.jobs`.

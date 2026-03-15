# Resume Upload & Parsing – Implementation Guide

This project uses **Vite + React** (not Next.js). The resume feature runs entirely in the client: upload to Supabase Storage, parse PDF in the browser, save parsed text to Supabase DB.

---

## STEP 1 – What to do in the Supabase Dashboard

### 1.1 Create the database table

In **Supabase Dashboard → SQL Editor**, run:

```sql
-- Resumes: one row per user, stores latest resume metadata + parsed text
create table public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  file_name text not null,
  storage_path text not null,
  file_size_bytes bigint,
  parsed_text text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id)
);

-- Optional: trigger to keep updated_at in sync
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger resumes_updated_at
  before update on public.resumes
  for each row execute function public.set_updated_at();

-- RLS: users can only read/insert/update/delete their own row
alter table public.resumes enable row level security;

create policy "Users can manage own resume"
  on public.resumes
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
```

**What you do manually:** Run the above SQL in Supabase → SQL Editor → New query → Run.

### 1.2 Create the Storage bucket

1. Go to **Storage** in the Supabase sidebar.
2. Click **New bucket**.
3. Name: `resumes`.
4. **Public bucket:** Off (we’ll allow access via RLS).
5. Click **Create bucket**.

### 1.3 Storage policies (for `resumes` bucket)

In **Storage → Policies** for the `resumes` bucket, add:

**Policy 1 – Allow authenticated upload (insert)**

- Policy name: `Authenticated users can upload resumes`
- Allowed operation: **INSERT**
- Target roles: `authenticated`
- USING expression: (leave empty)
- WITH CHECK expression: `bucket_id = 'resumes' and auth.uid()::text = (storage.foldername(name))[1]`

So: we store files under path `{user_id}/filename.pdf`. Only that user can upload into their folder.

**Policy 2 – Allow users to read their own files**

- Policy name: `Users can read own resumes`
- Allowed operation: **SELECT**
- Target roles: `authenticated`
- USING expression: `bucket_id = 'resumes' and auth.uid()::text = (storage.foldername(name))[1]`
- WITH CHECK: (leave empty)

**Policy 3 – Allow users to update/delete their own files**

- Policy name: `Users can update and delete own resumes`
- Allowed operation: **UPDATE** and **DELETE**
- Target roles: `authenticated`
- USING expression: `bucket_id = 'resumes' and auth.uid()::text = (storage.foldername(name))[1]`
- WITH CHECK: same as USING

**Optional – create bucket and policies via SQL**

In **SQL Editor** you can create the bucket and policies in one go (run after the table is created):

```sql
-- Create the bucket (run once)
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false);

-- Policy: authenticated users can upload only to their own folder
create policy "Users can upload own resumes"
on storage.objects for insert to authenticated
with check (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);

-- Policy: users can read their own files
create policy "Users can read own resumes"
on storage.objects for select to authenticated
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);

-- Policy: users can update/delete their own files
create policy "Users can update delete own resumes"
on storage.objects for update to authenticated
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "Users can delete own resumes"
on storage.objects for delete to authenticated
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
```

**What you do manually:** Either create the bucket and policies in the Storage UI, or run the SQL above (Supabase may expose `storage.buckets` and `storage.objects` in SQL Editor).

---

## STEP 2 – Dependencies to install

PDF parsing runs **in the browser** (no Node server). Use Mozilla’s PDF.js:

```bash
npm install pdfjs-dist
```

**Do not use `pdf-parse`** in this project—it is Node-only (uses `fs`) and won’t run in Vite’s client bundle.

**What you do manually:** Run `npm install pdfjs-dist` in the project root.

---

## STEP 3 – Architecture

Flow:

```
User selects PDF
  → Validate file (type, size)
  → Upload file to Supabase Storage (path: {user_id}/{filename})
  → Parse PDF in browser with pdfjs-dist → extract text
  → Upsert row in public.resumes (user_id, file_name, storage_path, parsed_text, etc.)
  → Resume page shows parsed text and option to replace resume
```

- **Storage:** one bucket `resumes`, paths `{user_id}/{filename}`.
- **Database:** one row per user in `public.resumes` (latest file name, path, parsed text).
- **No backend API:** upload and DB writes are done from the client using Supabase client.

---

## STEP 4 – Files to create or modify

| Action   | File |
|----------|------|
| Create   | `src/lib/resumeParser.ts` – extract text from PDF in browser |
| Create   | `src/lib/resumeService.ts` – upload to Storage + save/load from DB |
| Modify   | `src/pages/dashboard/Resume.tsx` – upload button, replace, show parsed text, loading/errors |

No changes to `supabaseClient.ts`; it already exists and is used by the new code.

---

## STEP 5 – Backend implementation (step by step)

**5.1 – `src/lib/resumeParser.ts`**  
- Validates file (PDF type, max 10MB).  
- Sets `GlobalWorkerOptions.workerSrc` for pdfjs-dist in Vite.  
- `parsePdfToText(file)` returns `{ text, pageCount }` using `getDocument` + `getTextContent` on each page.

**5.2 – `src/lib/resumeService.ts`**  
- `uploadResume(userId, file)`: validates → uploads to Storage `resumes/{userId}/{filename}` → parses PDF → upserts `public.resumes` (one row per user).  
- `getResume(userId)`: fetches the user’s resume row from `public.resumes`.

**5.3 – `src/pages/dashboard/Resume.tsx`**  
- On mount: get current user → `getResume(userId)` → set `resume` state.  
- Hidden `<input type="file" accept="application/pdf">`; “Upload Resume” / “Replace Resume” triggers it.  
- On file select: `uploadResume(userId, file)` → on success refresh `resume` state.  
- **Loading:** initial load shows spinner; during upload button shows `Loader2` and is disabled.  
- **Errors:** `error` for load failure; `uploadError` for validation/upload/DB errors, shown above the cards.  
- **Content:** “Your Resume” card shows file name, size, and parsed text (or “Upload a PDF…” / “No text could be extracted”).

---

## STEP 6 – Connect backend with Resume page UI

Done in STEP 5.3: the Resume page now:
- **Upload / Replace:** one button opens file picker; chosen PDF is uploaded, parsed, and saved; UI updates.  
- **Parsed text:** shown in “Your Resume” card in a scrollable area.  
- **Download PDF:** present but disabled until a resume exists (you can later wire it to a signed Storage URL).

---

## STEP 7 – Error handling and loading states

- **Initial load:** `loading` true → full-card spinner; `error` → red message card.  
- **Upload:** `uploadLoading` true → button shows spinner and is disabled; `uploadError` → red banner with message.  
- **Validation errors** (e.g. not PDF, >10MB) and **Supabase errors** (Storage/DB) are returned from `uploadResume` and shown as `uploadError`.

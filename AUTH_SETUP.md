# Supabase auth setup

This app uses **Vite + React** (not Next.js). Auth is implemented with Supabase and client-side route protection.

## 1. Environment variables

Create `.env.local` in the project root (or copy from `.env.example`):

```bash
# Supabase – from Supabase Dashboard → Project Settings → API
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

**Important:** Vite only exposes variables prefixed with `VITE_` to the client. Use `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, not `NEXT_PUBLIC_*`.

Restart the dev server after changing env vars.

## 2. Route protection (no middleware)

There is no `middleware.ts` in Vite. Protection is done with a **ProtectedRoute** component:

- All routes under `/app/*` are wrapped in `ProtectedRoute`.
- If the user is not authenticated, they are redirected to `/login`.

## 3. Auth flow

- **Signup** (`/signup`) → `supabase.auth.signUp()` → redirect to `/app/dashboard`
- **Login** (`/login`) → `supabase.auth.signInWithPassword()` → redirect to `/app/dashboard`
- **Logout** → Sidebar “Logout” button → `supabase.auth.signOut()` → redirect to `/login`

## 4. Session check

Use the helper in `src/lib/auth.ts`:

```ts
import { getCurrentUser } from "@/lib/auth";

const user = await getCurrentUser(); // User | null
```

## 5. Files reference

| Purpose           | File |
|------------------|------|
| Supabase client  | `src/lib/supabaseClient.ts` |
| Get current user | `src/lib/auth.ts` |
| Route guard      | `src/components/ProtectedRoute.tsx` |
| Login page       | `src/pages/Login.tsx` |
| Signup page      | `src/pages/Signup.tsx` |
| Logout           | `src/components/dashboard/Sidebar.tsx` (Logout button) |

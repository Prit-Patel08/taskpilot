/**
 * This project uses Vite + React Router (not Next.js).
 * There is no server middleware; route protection is done client-side.
 *
 * Protected routes: see src/components/ProtectedRoute.tsx
 * - All /app/* routes are wrapped with <ProtectedRoute> in src/App.tsx
 * - Unauthenticated users are redirected to /login
 */

export {};

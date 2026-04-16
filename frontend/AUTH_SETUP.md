# Authentication Setup

Authentication is backend-driven.

Rules:

* the frontend talks only to backend API endpoints
* the browser does not hold database credentials
* authentication is intended to be implemented with Auth0 through backend-managed routes

Current frontend placeholders:

* `POST /v1/auth/login`
* `POST /v1/auth/signup`
* `POST /v1/auth/logout`
* `GET /v1/auth/session`

Current frontend files:

* `src/services/api.ts`
* `src/lib/auth.ts`
* `src/components/ProtectedRoute.tsx`
* `src/pages/Login.tsx`
* `src/pages/Signup.tsx`
* `src/components/dashboard/Sidebar.tsx`

TODO:

* wire backend Auth0 login/session/logout handling
* replace placeholder responses with production auth flows

# Supabase authentication and user data

## Backend configuration

Set these names in the backend's local environment before starting the API:

- `SUPABASE_URL` — the Supabase project URL.
- `SUPABASE_PUBLISHABLE_KEY` — the project's publishable API key.

The backend-specific names take precedence. For the existing shared local
configuration, the backend also accepts `VITE_SUPABASE_URL` and
`VITE_SUPABASE_PUBLISHABLE_KEY` as fallback aliases. No secret or service-role
key is needed.

The backend does not need a Supabase secret or service-role key. The existing
MongoDB configuration remains separate. Do not put service credentials in the
frontend.

The API accepts Supabase Auth access tokens signed with the asymmetric `ES256`
or `RS256` algorithms. It verifies the signature against the project's public
JWKS using the certifi CA bundle with normal certificate and hostname
verification, then checks `iss`, `aud=authenticated`, `exp`, `sub`, the
authenticated role, and anonymous-account status. The `sub` must be a UUID. It
then uses the publishable key and the same bearer token with Supabase Auth's
`/auth/v1/user` endpoint to confirm the current user ID and
`email_confirmed_at`. A signed JWT alone does not contain a reliable
email-confirmation timestamp for this check. JWKS failures log the configured
endpoint hostname, available HTTP status, exception chain, and a redacted
message; they never log the token, API key, or complete URL.

Missing, expired, invalid-signature, wrong-issuer, or wrong-audience tokens
return `401`; unverified or anonymous identities return `403`. Missing or
malformed backend Supabase configuration returns `500`; a temporary network,
rate-limit, or upstream verification failure returns `503`; an invalid JWKS or
unexpected Supabase Auth response returns `502`. HS256 legacy signing is
deliberately unsupported: this backend does not accept or store a shared JWT
signing secret. Configure Supabase Auth to use an asymmetric signing key before
enabling personal-data endpoints.

`Authentication service is temporarily unavailable` is emitted by the
authentication dependency for a JWKS connection failure or a Supabase Auth
current-user lookup outage/rate limit/server error. A sanitized backend log
identifies which stage failed without recording tokens or provider response
bodies. A MongoDB profile operation failure has a separate `MongoDB operation
failed` response and sanitized log entry. A successful startup ping only checks
MongoDB at startup; it does not rule out a later collection/query failure.

## API boundary

Public endpoints remain available without a user token:

- `GET /`, `GET /api/health`, and `GET /api/db-health`
- `POST /api/food/analyze`
- `GET /api/food/photo`

The following endpoints require a verified Supabase user:

- `POST /api/meals`, `GET /api/meals`, and `DELETE /api/meals/{meal_id}`
- `GET /api/nutrition/daily`
- `GET /api/profile` and `PATCH /api/profile`

The owner ID is taken only from the verified JWT `sub`. Meal request schemas
reject extra fields such as `user_id`; query parameters never select an owner.
The API validates request and response shapes with Pydantic before writing or
returning documents.

## MongoDB collections

New records use separate `user_profiles` and `user_meals` collections. Profile
reads create an empty account-specific profile when one does not exist. A
profile stores `name`, `age`, `height_cm`, `weight_kg`, `activity_level`,
`goal`, `water_liters`, `dietary_preferences`, and the existing `targets`
subdocument for calories, protein, carbohydrates, and fats. The profile API
currently exposes `GET` and `PATCH`; both derive the owner from the verified
JWT and do not accept a caller-selected owner ID. Existing profile documents
that predate these personal fields return empty values for them and retain
their existing preferences and targets; no migration is needed.

Meal creation assigns `user_id` in the server service. Listing, daily
aggregation, and deletion always include the verified `user_id` in their
MongoDB filters. Deleting another user's guessed meal ID returns the same `404`
as a missing ID.

Startup creates these indexes:

- Unique `user_profiles.user_id`.
- `user_meals.user_id + meal_day + consumed_at` for date-filtered daily listing.
- `user_meals.user_id + consumed_at` for a user's recent-meal listing.

The application no longer creates or uses indexes on the legacy `meals` or
`profiles` collections. Existing documents in those collections are not read,
updated, deleted, copied, or assigned to an account by these routes. No
migration is performed. Any future migration must retain a backup, establish
record provenance and user consent, avoid assigning ambiguous shared records
to the first account, and be reviewed separately before execution.

## Frontend request contract

The frontend request helper in `src/api/client.js` now reads the current session
from `supabase.auth.getSession()` immediately before protected requests and
sends `Authorization: Bearer <session.access_token>` only to profile, meal, and
daily-nutrition endpoints. It does not log or persist the token, and it checks
that the session user matches the account scope captured by `src/App.jsx`.
Food analysis and photo lookup remain on the public request path. Supabase
session refresh is delegated to the SDK; a backend `401` is not retried in a
loop. Account changes, logout, and rejected sessions clear the frontend's
in-memory personal data and invalidate older requests before they can update
the current view. Profile and meal views are connected to the protected
endpoints. This frontend behavior does not replace backend token verification
or owner-scoped database queries.

## Email confirmation and redirect setup

The frontend explicitly uses Supabase's browser implicit callback handling
(`detectSessionInUrl`) for standard confirmation and recovery callbacks. It
only reports link-based confirmation success when Supabase has consumed an
actual callback payload and the resulting session contains a confirmed user.
For a scanner-resistant sign-up email, configure the Supabase confirmation
template to link to the requested redirect with a token hash, for example:

```html
<a href="{{ .RedirectTo }}&amp;token_hash={{ .TokenHash }}&amp;type=email">Confirm your email</a>
```

That callback presents an in-app confirmation button and calls the supported
`auth.verifyOtp` method only after the user clicks it. This avoids consuming
the one-time token during automatic link prefetching. The existing live
Supabase email template cannot be inspected from this repository; the template
must be checked and updated in the Dashboard if it still uses the direct
`{{ .ConfirmationURL }}` link.

Set `VITE_APP_PUBLIC_URL` explicitly in every environment to the app origin
that is intentionally allowlisted in Supabase. It must contain only the origin
(scheme, host, and optional port), not a path or query. The app does not infer
the redirect from the browser's current origin. Production origins must use
HTTPS. Local development may explicitly use `http://localhost:5173`, but that
link opens the Vite server only on the same machine.

For a second device on the same trusted LAN, use the development machine's LAN
IPv4 address as the frontend origin (for example, `http://192.168.1.25:5173`)
and set that exact origin as `VITE_APP_PUBLIC_URL`. Start Vite listening on LAN
interfaces with `npm run dev -- --host 0.0.0.0`; allow the port through the
development machine's firewall; and add the exact origin to Supabase's redirect
allowlist. The device must be on the same network and able to reach that host.
For personal API calls from the second device, also bind FastAPI to the LAN
interface, set `VITE_API_BASE_URL` to the backend's reachable LAN origin, and
include the frontend LAN origin in backend `CORS_ORIGINS`. Restart Vite after
changing frontend variables. Use a trusted network; if Supabase does not accept
the private-LAN HTTP redirect, use a reachable HTTPS development tunnel or
deploy the frontend instead. Do not assume a LAN address is reachable from the
public internet.

Add only exact local, LAN, and deployed callback origins that are in use to
Supabase's redirect allowlist; do not use an unrestricted wildcard. Confirmed
email status is still checked by the backend against Supabase Auth before
personal data is served.

## Local commands

From the repository root, install dependencies and run the isolated backend
tests:

```sh
cd backend
source venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

To start or restart the development API after setting the environment names
above in the backend's local environment file:

```sh
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

The backend tests use an in-memory fake MongoDB and mocked JWT key resolution
and Auth user lookup. They do not connect to MongoDB Atlas or Supabase.

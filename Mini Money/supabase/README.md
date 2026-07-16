# MiniMoney backend (Supabase)

Identity + parent/child access-linking layer only. NOT a sync of the core
mechanic (child profiles, tasks, Mbuck ledger, payslips) — that stays in the
Android app's local Room database for now. A linked child device passes the
access check but has no task/balance data until a separate sync migration
exists.

## What's here

- `migrations/0001_accounts_and_child_links.sql` — `parent_accounts` and
  `child_links` tables. RLS is enabled with no policies; every read/write
  goes through the Edge Functions below using the service_role key.
- `functions/auth-google` — parent sign-in. Verifies a Google ID token,
  upserts the parent account, issues an app session token.
- `functions/consent-current`, `functions/consent-accept` — POPIA consent,
  migrated off the old local debug mock so it's consistent with server-side
  identity.
- `functions/link-child` — parent registers a child's email as a PENDING
  link (max 4 per parent, mirrors the app's existing limit).
- `functions/access-check` — called by a child's device on launch. Claims a
  PENDING link on first sign-in with a matching email, or reports
  `allowed: false` so the app shows "Request access from a parent".

## Setup (founder does this — not something Claude can do)

1. Create a Supabase project at supabase.com. Note the Project URL (the app
   needs this) — the `service_role` key is set as a function secret by
   `supabase link`/CLI automatically and never needs to leave Supabase's
   own environment; it must never go in the Android app or be committed.
2. In Google Cloud Console, create an OAuth 2.0 Client ID for the Android
   app (Credential Manager / Google Identity Services). You'll need the
   app's SHA-1 signing fingerprint. Also note the Client ID string itself.
3. Install the Supabase CLI, then from this `supabase/` directory:
   ```
   supabase link --project-ref <your-project-ref>
   supabase db push
   supabase functions deploy auth-google consent-current consent-accept link-child access-check --no-verify-jwt
   supabase secrets set MINIMONEY_GOOGLE_CLIENT_IDS=<your-oauth-client-id>
   ```
4. Give Claude the Project URL and OAuth Client ID (NOT the service_role
   key or any password) to wire into the Android app's `build.gradle.kts`
   buildConfigField values.

`--no-verify-jwt` is required: these functions do their OWN auth (an
app-issued access_token via requireParentAuth, or a Google ID token
verified inline) rather than a Supabase Auth session JWT, so Supabase's
default gateway-level JWT check would reject every legitimate call.

## Local dev (optional)

`supabase start` runs the whole stack in Docker. `supabase functions serve`
hot-reloads the Edge Functions against it. Set `MINIMONEY_GOOGLE_CLIENT_IDS`
in `supabase/.env.local` (gitignored) for local testing.

-- MiniMoney identity/linking layer.
--
-- Scope boundary (deliberate, see project notes): these two tables handle
-- Google Sign-In identity and parent<->child ACCESS LINKING only. They are
-- NOT a sync of the core mechanic (child profiles, tasks, Mbuck ledger,
-- payslips) — that data remains local-only in the Android app's Room
-- database for now. A child device that passes the access check here still
-- has no task/balance data until a separate data-sync migration exists.
--
-- child_links.google_sub is globally unique when set: a given child Google
-- account can be linked to exactly one parent. That uniqueness IS the "is
-- this minor allowed in" check the app performs on every launch.
--
-- A parent only ever knows their child's EMAIL, never their opaque Google
-- subject ID (Google does not expose an email->sub lookup to third-party
-- apps). So a row starts PENDING (google_sub null, email set by the parent)
-- and is CLAIMED the first time a device signs in with a verified Google ID
-- token whose email matches — at that moment google_sub is filled in from
-- the token and becomes the authoritative identifier from then on (so a
-- later email change on the child's Google account can't orphan or hijack
-- the link). See supabase/functions/access-check.

create table if not exists parent_accounts (
    id uuid primary key default gen_random_uuid(),
    google_sub text not null unique,       -- Google's stable subject identifier — never the email (emails can change)
    email text not null,
    display_name text,
    access_token text unique,              -- app-issued session token; regenerated on each sign-in (single active session)
    -- POPIA consent (BuildSpec §Compliance) — structurally separate from
    -- registration; tracked here so it's consistent across a parent's
    -- devices now that identity itself is server-side.
    consent_version text,
    consent_accepted_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists child_links (
    id uuid primary key default gen_random_uuid(),
    parent_account_id uuid not null references parent_accounts(id) on delete cascade,
    google_sub text unique,                -- null while PENDING; set (and immutable) once CLAIMED
    email text not null,                   -- the email the parent registered; used only for the one-time claim match
    display_name text,
    -- Mirrors app.domain.child.AgeBand exactly (three-tier model, PRD §Personas).
    age_band text not null check (age_band in ('SIX_TO_NINE', 'TEN_TO_FOURTEEN', 'FIFTEEN_TO_EIGHTEEN')),
    claimed_at timestamptz,                -- null while PENDING
    created_at timestamptz not null default now()
);

create index if not exists idx_child_links_parent_account_id on child_links(parent_account_id);

-- Prevents two different parents from both registering the same pending
-- email (which would make the first-sign-in claim in access-check
-- ambiguous — see link-child's 23505 handling, which relies on this).
-- Case-sensitivity is handled by link-child always lower-casing before
-- insert/lookup, so a plain unique index is sufficient here.
create unique index if not exists idx_child_links_pending_email
    on child_links(email) where google_sub is null;

-- Deny-by-default: no anon/authenticated policies are defined. All access
-- goes through Edge Functions using the service_role key (server-side only,
-- never shipped to the client) — see supabase/functions/.
alter table parent_accounts enable row level security;
alter table child_links enable row level security;

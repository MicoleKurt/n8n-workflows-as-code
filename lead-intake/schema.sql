-- Run once in your Postgres (Supabase SQL Editor, Neon, etc.) before
-- executing the workflow. The Postgres nodes upsert on `email`.

create table if not exists public.leads (
  id               bigint generated always as identity primary key,
  lead_id          text        not null,
  full_name        text        not null,
  email            text        not null unique,
  company          text        not null,
  country          text,
  service_interest text,
  monthly_budget   numeric(12,2) default 0,
  lead_score       int         not null default 0,
  lead_tier        text        not null check (lead_tier in ('hot','warm','cold')),
  status           text        not null default 'new',
  assigned_to      text,
  notes            text,
  created_at       timestamptz not null default now()
);

create index if not exists leads_tier_score_idx
  on public.leads (lead_tier, lead_score desc);

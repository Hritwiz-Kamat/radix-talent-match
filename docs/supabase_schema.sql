-- Run ONCE in Supabase: Dashboard -> SQL Editor -> New query -> paste -> Run.
-- One generic JSONB table = the "JSON for most things" the brief asks for.

create table if not exists public.documents (
  kind        text        not null,          -- 'profiles' | 'jd' | 'resume' | 'results' | 'company_skillsets'
  key         text        not null,          -- e.g. 'ananya-rao'
  data        jsonb       not null,          -- the contract object (schemas.py) as JSON
  updated_at  timestamptz not null default now(),
  primary key (kind, key)
);

-- Lock it down: with RLS on and NO policies, the public/anon key can read and write nothing.
-- Only our backend (service_role key) can touch it. Never put that key in the frontend.
alter table public.documents enable row level security;

-- Private bucket for uploaded CVs and uploaded JD/resume files
insert into storage.buckets (id, name, public)
values ('candidate-files', 'candidate-files', false)
on conflict (id) do nothing;

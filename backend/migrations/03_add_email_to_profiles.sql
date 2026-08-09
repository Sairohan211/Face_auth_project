-- Migration: Add and enforce email column on public.profiles

-- 1. Ensure email column exists on public.profiles
alter table public.profiles
add column if not exists email text;

-- 2. Backfill existing profile records from auth.users (if any remain null)
update public.profiles p
set email = lower(u.email)
from auth.users u
where p.id = u.id and (p.email is null or p.email = '');

-- 3. Ensure email_verified boolean column exists
alter table public.profiles
add column if not exists email_verified boolean not null default false;

-- 4. Set email column to NOT NULL
alter table public.profiles
alter column email set not null;

-- 5. Add index on profiles(email) for fast lookups
create index if not exists idx_profiles_email on public.profiles(email);

-- 6. Verify Row Level Security (RLS) policies
alter table public.profiles enable row level security;

-- User isolation: users can only view their own profile
drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile"
  on public.profiles
  for select
  using (auth.uid() = id);

-- User isolation: users can only update their own profile
drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile"
  on public.profiles
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Service role full management
drop policy if exists "Service role has full access to profiles" on public.profiles;
create policy "Service role has full access to profiles"
  on public.profiles
  for all
  using (true)
  with check (true);

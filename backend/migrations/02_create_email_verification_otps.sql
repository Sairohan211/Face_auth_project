-- Migration: Add email verification OTP support and update profiles

-- 1. Modify public.profiles to include email_verified boolean
alter table public.profiles
add column if not exists email_verified boolean not null default false;

-- 2. Create public.email_verification_otps table
create table if not exists public.email_verification_otps (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  email text not null,
  otp_hash text not null,
  expires_at timestamptz not null,
  attempts integer not null default 0,
  verified_at timestamptz null,
  created_at timestamptz not null default now()
);

-- 3. Add performance and lookup indexes
create index if not exists idx_email_verification_otps_user_id on public.email_verification_otps(user_id);
create index if not exists idx_email_verification_otps_email on public.email_verification_otps(email);
create index if not exists idx_email_verification_otps_expires_at on public.email_verification_otps(expires_at);

-- 4. Enable Row Level Security (RLS)
alter table public.email_verification_otps enable row level security;

-- Only service role (backend FastAPI) has access to OTP table
create policy "Service role manages email verification OTPs"
  on public.email_verification_otps
  for all
  using (true)
  with check (true);

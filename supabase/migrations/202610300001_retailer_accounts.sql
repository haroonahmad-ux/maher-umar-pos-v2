-- Retailer identity is separate from each device's local SQLite business database.
create table if not exists public.retailer_accounts (
    user_id uuid primary key references auth.users(id) on delete cascade,
    username text not null,
    phone text not null,
    phone_verified boolean not null default false,
    created_at timestamptz not null default now()
);
create unique index if not exists retailer_accounts_username_lower_uq
    on public.retailer_accounts (lower(username));
create unique index if not exists retailer_accounts_phone_uq
    on public.retailer_accounts (phone);

create table if not exists public.retailer_auth_attempts (
    id bigint generated always as identity primary key,
    ip_hash text not null,
    created_at timestamptz not null default now()
);
create index if not exists retailer_auth_attempts_ip_created_idx
    on public.retailer_auth_attempts (ip_hash, created_at desc);

alter table public.retailer_accounts enable row level security;
alter table public.retailer_auth_attempts enable row level security;
revoke all on public.retailer_accounts from anon, authenticated;
revoke all on public.retailer_auth_attempts from anon, authenticated;
grant all on public.retailer_accounts to service_role;
grant all on public.retailer_auth_attempts to service_role;

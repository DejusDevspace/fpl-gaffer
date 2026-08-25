-- 004_subscriptions.sql
-- Adds subscription/tier tracking for FPL Gaffer.

create type subscription_tier as enum ('free', 'basic', 'pro');
create type subscription_status as enum ('active', 'canceled', 'past_due', 'incomplete');
create type billing_provider as enum ('stripe', 'paystack');

create table public.subscriptions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    tier subscription_tier not null default 'free',
    status subscription_status not null default 'active',
    provider billing_provider,
    provider_customer_id text,
    provider_subscription_id text,
    current_period_end timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id)
);

alter table public.subscriptions enable row level security;

create policy "Users can read their own subscription"
    on public.subscriptions for select
    using (auth.uid() = user_id);

create index idx_subscriptions_user_id on public.subscriptions(user_id);
create index idx_subscriptions_provider_subscription_id on public.subscriptions(provider_subscription_id);

create or replace function update_subscriptions_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger set_subscriptions_updated_at
    before update on public.subscriptions
    for each row execute function update_subscriptions_updated_at();

create table devices (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    name text not null,
    device_type text not null check (device_type in ('pc', 'mobile', 'third_party')),
    created_at timestamptz default now()
);

create table rooms (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    name text not null,
    created_at timestamptz default now()
);

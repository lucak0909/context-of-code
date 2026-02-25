create table public.users (
  id uuid not null default gen_random_uuid (),
  email text not null,
  created_at timestamp with time zone null default now(),
  constraint users_pkey primary key (id),
  constraint users_email_key unique (email)
) TABLESPACE pg_default;
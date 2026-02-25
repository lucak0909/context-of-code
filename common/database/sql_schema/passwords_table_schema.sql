create table public.passwords (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  password_enc text not null,
  created_at timestamp with time zone null default now(),
  constraint passwords_pkey primary key (id),
  constraint passwords_user_id_key unique (user_id),
  constraint passwords_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
) TABLESPACE pg_default;
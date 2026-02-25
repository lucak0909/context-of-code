create table public.devices (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  name text not null,
  device_type text not null,
  created_at timestamp with time zone null default now(),
  constraint devices_pkey primary key (id),
  constraint devices_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE,
  constraint devices_device_type_check check (
    (
      device_type = any (
        array['pc'::text, 'mobile'::text, 'third_party'::text]
      )
    )
  )
) TABLESPACE pg_default;
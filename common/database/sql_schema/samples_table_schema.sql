create table public.samples (
  id bigserial not null,
  device_id uuid not null,
  sample_type text not null,
  ts timestamp with time zone not null,
  wifi_rssi_dbm numeric null,
  link_speed_mbps numeric null,
  is_connected boolean null,
  latency_ms numeric null,
  packet_loss_pct numeric null,
  down_mbps numeric null,
  up_mbps numeric null,
  ip text null,
  latency_eu_ms numeric null,
  latency_us_ms numeric null,
  latency_asia_ms numeric null,
  created_at timestamp with time zone null default now(),
  test_method text null,
  constraint samples_pkey primary key (id),
  constraint samples_device_id_fkey foreign KEY (device_id) references devices (id) on delete CASCADE,
  constraint samples_sample_type_check check (
    (
      sample_type = any (
        array[
          'mobile_wifi'::text,
          'desktop_network'::text,
          'cloud_latency'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;
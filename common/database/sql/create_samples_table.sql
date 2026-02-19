create table samples (
    id bigserial primary key,

    device_id uuid not null references devices(id) on delete cascade,
    room_id uuid references rooms(id) on delete set null,

    sample_type text not null 
        check (sample_type in ('mobile_wifi', 'desktop_network', 'cloud_latency')),

    ts timestamptz not null,

    -- Mobile WiFi metrics
    wifi_rssi_dbm numeric,
    link_speed_mbps numeric,
    is_connected boolean,

    -- Desktop network metrics
    latency_ms numeric,
    packet_loss_pct numeric,
    down_mbps numeric,
    up_mbps numeric,
    test_method text,

    -- Cloud latency metrics
    latency_eu_ms numeric,
    latency_us_ms numeric,
    latency_asia_ms numeric,

    created_at timestamptz default now()
);

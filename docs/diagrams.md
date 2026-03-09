# Context of Code — System Diagrams

> Preview with: `Cmd+Shift+V` (requires [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid))

---

## 1. Project Structure

```mermaid
graph TD
    Root["📁 context-of-code/"]

    Root --> Agent["📁 agent/"]
    Root --> WebApp["📁 web_app/"]
    Root --> Common["📁 common/"]
    Root --> Frontend["📁 frontend/"]

    Agent --> AgentEntry["__main__.py · entry point"]
    Agent --> PCCollector["📁 pc_data_collector/\nDataCollector · get_network_metrics()"]
    Agent --> CloudCollector["📁 cloud_latency_collector/\nbackground thread · pings EU/US/Asia"]
    Agent --> UQueue["📁 uploader_queue/\nUploadQueue · file-backed retry queue"]

    PCCollector --> CLIAuth["cli/console_auth.py · login prompt"]
    PCCollector --> MainPy["main.py · run() · run_with_user()"]

    WebApp --> AppPy["app.py · Flask + CORS · /health"]
    WebApp --> BP["📁 blueprints/"]
    BP --> ApiPy["api.py · POST /api/ingest"]
    BP --> ReportPy["reporting.py · GET /api/report/*"]
    BP --> AuthPy["auth.py · POST /api/auth/*"]

    Common --> DBDir["📁 database/"]
    DBDir --> ORM["db_dataclasses.py · ORM models\nUser · Password · Device · Sample"]
    DBDir --> DBOps["db_operations.py · Database class\ninsert · query · get_or_create_device"]
    Common --> Settings["settings.py · env config"]

    Frontend --> AppJSX["App.jsx · polls every 60s"]
    Frontend --> ApiJS["api.js · fetch wrappers"]
    Frontend --> Charts["NetworkChart · BytesChart\nTcpConnectionsChart · MobileChart"]
    Frontend --> UIComp["AuthScreen · DeviceSelector\nMetricCard · StatusBadge"]
```

---

## 2. Demo Flowchart

```mermaid
flowchart TD
    A([Student runs: python3 -m agent]) --> B[Console login\nenter email + password]
    B --> C[Lookup or create Device record\nin Supabase via SQLAlchemy]
    C --> D[Start collection loop\nevery 30 seconds]

    D --> E[DataCollector.get_network_metrics\nlatency · packet loss · download · upload\nTCP connections · bytes sent · bytes recv]
    E --> F[Build JSON payload\ndevice_id · ts · sample_type · metrics]
    F --> G[UploadQueue.enqueue\nappend to agent_queue.jsonl]
    G --> H[UploadQueue.flush\nread queue file, POST each payload]

    H --> I{VM reachable?}
    I -->|Yes| J["POST /api/ingest\nhttp://200.69.13.70:5017"]
    I -->|No - network down| K[Keep payload in queue\nretry next cycle]

    J --> L[Flask validates JSON\nextract device_id, sample_type, ts]
    L --> M[SQLAlchemy inserts row\ninto Supabase samples table]
    M --> N([New row visible in Supabase])

    N --> O[React frontend polls\nGET /api/report/samples every 60s]
    O --> P([Charts update live\nLatency · Download · Upload\nTCP Connections · Network Bytes])

    K --> D
    D --> D
```

---

## 3. Full System Architecture

```mermaid
graph LR
    subgraph Laptop["🖥️ Student Laptop"]
        direction TB
        Collector["DataCollector\npsutil · speedtest\nevery 30s"]
        CloudThread["CloudLatencyCollector\nbg thread · EU / US / Asia pings"]
        Queue["UploadQueue\nagent_queue.jsonl\nretry buffer"]
        Collector -->|enqueue payload| Queue
        CloudThread -->|enqueue payload| Queue
    end

    subgraph VM["☁️ VM  ·  200.69.13.70:5017\ncontext-of-code.service  ·  Gunicorn × 5"]
        direction TB
        Ingest["POST /api/ingest\nvalidate · route by sample_type"]
        Report["GET /api/report/samples\nGET /api/report/devices\nGET /api/report/latest"]
        Auth["POST /api/auth/login\nPOST /api/auth/register"]
        Health["GET /health"]
    end

    subgraph Supabase["🗄️ Supabase\naws-1-eu-north-1"]
        direction TB
        Users["users"]
        Devices["devices"]
        Samples["samples\ndesktop_network\ncloud_latency\nmobile_wifi"]
        Users --> Devices --> Samples
    end

    subgraph Browser["🌐 Browser"]
        direction TB
        FE["React Frontend\nNetworkChart · BytesChart\nTcpConnectionsChart · MobileChart\nCloud Latency · Mobile WiFi"]
    end

    Queue -->|"HTTP POST every 30s"| Ingest
    Ingest -->|"SQLAlchemy INSERT"| Samples
    FE -->|"fetch every 60s"| Report
    Report -->|"SQLAlchemy SELECT"| Samples
    FE -->|login / register| Auth
    Auth -->|user lookup| Users
    FE -->|"ping /health"| Health
```

---

## 4. Data Flow Sequence

```mermaid
sequenceDiagram
    actor Student
    participant Collector as DataCollector<br/>(pc_data_collector)
    participant Queue as UploadQueue<br/>(agent_queue.jsonl)
    participant VM as VM Flask API<br/>(:5017/api/ingest)
    participant DB as Supabase<br/>(samples table)
    participant FE as React Frontend

    Student->>Collector: python3 -m agent (login)
    Collector->>DB: get_or_create_device(user_id, hostname)
    DB-->>Collector: device_id (UUID)

    loop Every 30 seconds
        Collector->>Collector: get_network_metrics()<br/>latency · packet loss · download · upload<br/>tcp_connections · bytes_sent · bytes_recv
        Collector->>Queue: enqueue(payload)
        Queue->>Queue: append JSON line to agent_queue.jsonl
        Queue->>VM: POST /api/ingest  {device_id, sample_type, ts, ...metrics}
        VM->>VM: validate device_id (UUID)<br/>parse optional fields<br/>route by sample_type
        VM->>DB: INSERT INTO samples (SQLAlchemy ORM)
        DB-->>VM: row committed
        VM-->>Queue: 200 {"status": "ok"}
        Queue->>Queue: remove sent line from queue file
    end

    loop Every 60 seconds
        FE->>VM: GET /api/report/samples?device_id=...&hours=1
        VM->>DB: SELECT * FROM samples WHERE device_id=... AND ts >= cutoff
        DB-->>VM: array of sample rows
        VM-->>FE: JSON array
        FE->>FE: re-render charts<br/>(Latency · Download · Upload<br/>TCP Connections · Network Bytes)
    end
```

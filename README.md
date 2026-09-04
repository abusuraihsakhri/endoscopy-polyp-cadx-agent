# Endoscopy Polyp CADX Agent

> **Domain:** Clinical Decision Support & Gastroenterology AI  
> **Standards:** CAP / CLSI / ISO / ESGE / NICE Endoscopic Polyp Criteria

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Endoscopy Polyp CADX Agent is a clinical decision support system for real-time colorectal polyp classification during colonoscopy. It combines three specialized worker agents to evaluate endoscopic findings and produce consensus dossiers with cryptographic audit trails.

The system uses NBI (Narrow Band Imaging) pit pattern analysis with NICE/WASP optical criteria to classify polyps as adenomatous vs hyperplastic, supporting clinicians in making resection decisions.

---

## ⚙️ Architecture

The project contains two complementary modules:

| Module | Path | Purpose |
|:-------|:-----|:--------|
| **Primary Agent Suite** | `agents/` | Core multi-worker evaluation with Zero-PHI guard and HMAC audit |
| **EndoCADx Engine** | `endo_cadx_agent/` | Alternative coordinator with ESGE/NICE standard conformance |

### Key Components

- **Zero-PHI Outbound Guard** (`agents/base.py`): Regex-based inspection blocking SSNs, MRNs, phone numbers, emails, DOB patterns, and patient names from any outbound data.
- **HMAC-SHA256 Audit Trail** (`agents/base.py`): Chained, cryptographically signed logs for every evaluation. Requires `AUDIT_SECRET_KEY` environment variable in production.
- **Three Specialized Workers** (`agents/workers.py`):
  - `InvariantQCWorker`: Primary metric threshold monitoring (>25.0)
  - `SafetyEscalationWorker`: Critical flag and secondary metric interlock (>12.0)
  - `ProtocolConformanceWorker`: Status descriptor anomaly detection
- **Supervisor** (`agents/supervisor.py`): Orchestrates workers and produces consensus dossiers
- **Enrichment Engines** (`enrichment.py`): Seven domain-specific evaluation modules with shared threshold logic

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuaihsakhri/endoscopy-polyp-cadx-agent.git
cd endoscopy-polyp-cadx-agent

# Install core dependencies
pip install -e .

# Install with web server support
pip install -e ".[web]"

# Install with development tools
pip install -e ".[dev]"
```

### Environment Variables

| Variable | Required | Description |
|:---------|:---------|:------------|
| `AUDIT_SECRET_KEY` | Recommended | HMAC-SHA256 key for audit trail signing. A random key is generated at startup if not set. |

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 💻 CLI Usage

### 1. Single Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --target SPECIMEN-01 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Supervisory Chat Query
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch CSV Processing
```bash
python cli.py batch -i sample.csv -o results.csv
```

The CSV must include columns: `task_id`, `target_identifier`, `primary_metric`, `secondary_metric`, `is_critical_flag`, `status_descriptor`.

### 4. Verify Audit Trail Integrity
```bash
python cli.py verify-audit
```

### 5. Launch REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

---

## 🌐 REST API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/health` | Health check and system metadata |
| `GET` | `/metrics` | Prometheus operational metrics |
| `POST` | `/api/audit` | Submit task payload for evaluation |
| `POST` | `/api/chat` | Supervisory conversational query |
| `GET` | `/api/audit/logs` | Retrieve and verify HMAC audit trail |

### Example API Request
```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "TASK-001",
    "target_identifier": "SPECIMEN-01",
    "primary_metric": 28.5,
    "secondary_metric": 14.2,
    "status_descriptor": "DISCORDANT_ANOMALY",
    "is_critical_flag": true
  }'
```

---

## 🛡️ Security Features

* **Zero-PHI Outbound Interceptor:** Blocks SSNs, MRNs, phone numbers, emails, DOB patterns, and patient names from outbound data
* **Input Validation:** All task_id and target_identifier fields are validated for length and content
* **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
* **Bounds Checking:** Primary and secondary metrics validated as finite numbers
* **CSV Input Limits:** Batch processing enforces 100MB file size limit

---

## 🧪 Testing

Run the automated test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest -v --tb=short
```

Execute high-throughput batch simulation:

```bash
python simulator.py 100
```

---

## 🐳 Container Deployment

```bash
docker build -t endoscopy-polyp-cadx-agent .
docker run -e AUDIT_SECRET_KEY=<your-secret-key> -p 8000:8000 endoscopy-polyp-cadx-agent
```

Or with Docker Compose:

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
endoscopy-polyp-cadx-agent/
├── agents/                  # Primary agent suite
│   ├── api.py               # FastAPI REST endpoints
│   ├── base.py              # PHI guard, HMAC audit, security
│   ├── models.py            # Pydantic data models
│   ├── supervisor.py        # Multi-worker orchestrator
│   ├── workers.py           # Specialized evaluation workers
│   ├── llm_factory.py       # LLM provider abstraction
│   ├── learning.py          # Bayesian calibration engine
│   ├── metrics.py           # Prometheus metrics collector
│   └── streamer.py          # WebSocket telemetry broadcaster
├── endo_cadx_agent/         # Alternative EndoCADx engine
│   ├── agents.py            # Sub-agent implementations
│   ├── engine.py            # Core evaluation engine
│   ├── models.py            # Data models
│   ├── cli.py               # CLI entry point
│   └── server.py            # FastAPI server factory
├── tests/                   # Test suite
├── web/index.html           # Operations console UI
├── cli.py                   # Main CLI entry point
├── enrichment.py            # Domain enrichment engines
├── simulator.py             # Stress testing simulator
├── pyproject.toml           # Project configuration
├── Dockerfile               # Container build
└── docker-compose.yml       # Multi-service orchestration
```

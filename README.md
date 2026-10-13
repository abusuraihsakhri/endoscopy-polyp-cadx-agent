# Endoscopy Polyp CADx Agent

A research-oriented **rule-evaluation demonstration** for synthetic endoscopy-related task parameters. The software evaluates two numerical metrics, a status descriptor, and a critical escalation flag. It produces rule alerts, synthetic dossiers, and (in the Python supervisor) a chained HMAC-SHA256 audit record.

**Clinical limitation:** Despite the historical project name, this repository does **not** contain an endoscopy image model, NBI feature extraction, trained optical classifier, NICE/WASP category assignment, histology prediction, clinical validation, or a polypectomy decision algorithm. The threshold values 25 and 12 are demonstration parameters, **not clinical decision thresholds**. Do not use the results for patient care.

## Browser demonstration

Open [`web/index.html`](web/index.html) in a modern desktop or mobile browser. Enter **synthetic** task/target identifiers, numerical values, a descriptor, and a critical flag, then select **Evaluate rules**. Results may be exported as a JSON file. The interface implements the same three simple rules as the primary Python workers, with no cryptographic signature.

The static site is eligible for deployment through the GitHub Pages workflow (`.github/workflows/pages.yml`). GitHub Pages must use **GitHub Actions** as its build and deployment source. A verified live URL will be linked here when available.

The browser demo runs locally with JavaScript: no Pyodide, Python server, model downloads, external fonts, network requests, cookies, or browser storage are required.

## Installation

Requires Python 3.10–3.12 for the CI-tested versions (project metadata permits Python 3.9+).

```bash
git clone https://github.com/abusuraihsakhri/endoscopy-polyp-cadx-agent.git
cd endoscopy-polyp-cadx-agent
python -m pip install -e ".[web,dev]"
pytest -v
```

Two command-line interfaces are retained:

- `endoscopy-polyp-cadx-agent` (equivalent to `python cli.py`): primary `agents/` supervisor with HMAC audit trail.
- `endoscopy-polyp-cadx-engine` (equivalent to `python -m endo_cadx_agent.cli`): separate `endo_cadx_agent/` threshold engine.

### Primary CLI

```bash
endoscopy-polyp-cadx-agent audit --task-id DEMO-001 --target SAMPLE-001 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
endoscopy-polyp-cadx-agent batch -i sample.csv -o results.csv
endoscopy-polyp-cadx-agent verify-audit
endoscopy-polyp-cadx-agent chat "What is the system status?"
endoscopy-polyp-cadx-agent serve --host 127.0.0.1 --port 8000
```

Batch processing reads a UTF-8 CSV; example columns are in [`sample.csv`](sample.csv). Invalid rows are skipped and produce exit code 2; invalid/absent files produce exit code 1. Spreadsheet formula-looking cells are escaped in the exported CSV. `verify-audit` reports HMAC signature integrity for the **current in-memory session** and exits unsuccessfully if verification fails.

### REST API

The primary service is in `agents/api.py`:

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Health and metadata |
| GET | `/metrics` | JSON counters for in-memory sessions |
| POST | `/api/audit` | Apply three deterministic rules to a task payload |
| POST | `/api/chat` | Deterministic mock answer; no LLM service |
| GET | `/api/audit/logs` | Audit metadata (requires explicitly configured token) |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task_id":"DEMO-001","target_identifier":"SAMPLE-001","primary_metric":28.5,"secondary_metric":14.2,"status_descriptor":"DISCORDANT","is_critical_flag":false}'
```

The primary worker rules are: primary metric greater than 25 gives an elevated alert; secondary metric greater than 12 gives an elevated alert; the critical flag produces a critical alert; and descriptor keywords such as `DISCORDANT`, `ANOMALY`, `MUTANT`, `VIOLATION`, `FAIL`, or `REJECT` produce an elevated alert. These are **software tests**, not evidence-based polyp diagnostic criteria. The alternate engine uses different thresholds; its output is not interchangeable.

## Security and data handling

The Python supervisor performs **limited regex-based detection** of selected PHI-like strings. **This is not complete de-identification, HIPAA Safe Harbor compliance, or proof of patient-data safety.** Use synthetic data only. The REST API has no general authentication and must not be exposed publicly without an appropriate gateway.

Audit-log retrieval is disabled unless an operator configures `AUDIT_LOGS_TOKEN`. When enabled, send the token in the `X-Audit-Token` request header. The audit trail is held in process memory, is **not persisted**, and each process normally uses a random signing key unless `AUDIT_SECRET_KEY` is set. Audit integrity checks recompute HMACs but cannot authenticate an operator or protect against a compromised signing key.

For the container setup, provide a unique strong signing key before startup (do not commit it):

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
docker compose up --build
```

A fixed audit key previously appeared in repository history. **Do not reuse it**; treat it as disclosed and rotate any deployment that used it. Prefer HTTPS and an authentication proxy for external API access.

## Development

```bash
python -m pip install -e ".[web,dev]"
python -m compileall -q agents endo_cadx_agent cli.py enrichment.py simulator.py
pytest -v
ruff check --select E4,E7,E9 .
python simulator.py 100
```

GitHub Actions tests Python 3.10–3.12, checks Python/JavaScript syntax, and deploys the `web/` directory to GitHub Pages when configured. Python code requires a local interpreter or server; **GitHub Pages hosts only the independent JavaScript demonstration**.

The source packages are `agents/` (primary Pydantic/FastAPI workers) and `endo_cadx_agent/` (legacy alternate dataclass evaluator). `enrichment.py` contains supplementary synthetic threshold demonstrations, not implemented clinical CADx pipelines.

## License

[MIT](LICENSE).

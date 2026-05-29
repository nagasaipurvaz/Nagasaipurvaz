# 🏥 Enterprise Healthcare GenAI Platform

> AI-powered clinical co-pilots & agentic care management systems with HIPAA compliance

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.36-purple.svg)](https://crewai.com)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-red.svg)](https://hl7.org/fhir/R4/)
[![HIPAA](https://img.shields.io/badge/HIPAA-Compliant-brightgreen.svg)](#hipaa-compliance)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI REST API (v1)                       │
│          /api/v1/clinical   ·   /api/v1/care                    │
└──────────────────────┬────────────────┬────────────────────────┘
                       │                │
          ┌────────────▼──┐    ┌────────▼──────────┐
          │  LangGraph    │    │  CrewAI            │
          │  Clinical     │    │  Care Management  │
          │  Co-pilot     │    │  Crew              │
          └──────┬────────┘    └────────┬──────────┘
                 │                      │
          ┌──────▼──────────────────────▼──────────┐
          │           Tool Layer                    │
          │  FHIR Tools  ·  Clinical Tools          │
          │  (search, conditions, meds, vitals)     │
          └──────────────────┬─────────────────────┘
                             │
          ┌──────────────────▼─────────────────────┐
          │           FHIR R4 Server               │
          │      (HAPI FHIR or EHR system)         │
          └────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────┐
  │                    HIPAA Compliance Layer                    │
  │   Audit Logger · PHI Redactor · Role-Based Access Control   │
  └──────────────────────────────────────────────────────────────┘
```

---

## Core Features

### 🤖 AI Agents

| Agent | Framework | Description |
|-------|-----------|-------------|
| **Clinical Co-pilot** | LangGraph | ReAct agent with FHIR + clinical tools; generates structured clinical summaries |
| **Patient Assessment** | LangGraph | Multi-step triage → risk stratification → notification workflow |
| **Care Management Crew** | CrewAI | 4-agent crew: Coordinator · Clinical Analyst · Social Worker · Care Plan Writer |

### 🏥 Clinical Capabilities

- **Risk Stratification** — Evidence-based 30-day readmission risk (Charlson + LACE)
- **Drug Interaction Checking** — Known interaction database with severity levels
- **Care Gap Identification** — USPSTF guideline adherence monitoring
- **FHIR R4 Integration** — Patient, Condition, MedicationRequest, Observation resources
- **AI Care Plan Generation** — FHIR CarePlan-compatible structured output

### 🔒 HIPAA Compliance

| Feature | Implementation |
|---------|---------------|
| **Audit Trail** | Append-only, SHA-256 chained audit log (tamper-evident) |
| **PHI Detection** | Regex-based 18-identifier Safe Harbor redaction |
| **Access Control** | JWT + RBAC (Physician / Nurse / Care Manager / Auditor / Admin) |
| **Minimum Necessary** | Per-endpoint permission checks |
| **7-Year Retention** | Configurable audit log retention (default: 2555 days) |

---

## Project Structure

```
healthcare-genai-platform/
├── src/
│   ├── agents/
│   │   ├── clinical_copilot.py    # LangGraph ReAct agent
│   │   └── care_manager.py        # CrewAI 4-agent crew
│   ├── workflows/
│   │   └── patient_assessment.py  # LangGraph state machine
│   ├── tools/
│   │   ├── fhir_tools.py          # FHIR R4 LangChain tools
│   │   └── clinical_tools.py      # Risk/interaction/gap tools
│   ├── hipaa/
│   │   ├── audit_logger.py        # Chained tamper-evident audit log
│   │   ├── phi_redactor.py        # 18-identifier PHI detection
│   │   └── access_control.py      # JWT + RBAC
│   ├── models/
│   │   ├── patient.py             # FHIR Patient model
│   │   └── care_plan.py           # FHIR CarePlan model
│   ├── api/
│   │   ├── main.py                # FastAPI app
│   │   └── routes/
│   │       ├── clinical.py        # Co-pilot & assessment endpoints
│   │       └── care_management.py # Care plan generation endpoint
│   └── config/
│       └── settings.py            # Pydantic settings
├── tests/
│   ├── test_hipaa.py              # HIPAA audit & PHI tests
│   └── test_clinical_tools.py     # Clinical logic tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd healthcare-genai-platform
cp .env.example .env
# Edit .env — set OPENAI_API_KEY and FHIR_BASE_URL
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

Services started:
- **API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs
- **FHIR Server** → http://localhost:8080
- **PostgreSQL** → localhost:5432
- **Redis** → localhost:6379

### 3. Run locally (development)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

uvicorn src.api.main:app --reload
```

### 4. Run tests

```bash
pytest tests/ -v --cov=src
```

---

## API Reference

### Clinical Co-pilot

```http
POST /api/v1/clinical/copilot
Authorization: Bearer <jwt>

{
  "patient_id": "patient-123",
  "query": "Summarize this patient's risk profile and recommend interventions."
}
```

**Response:**
```json
{
  "patient_id": "patient-123",
  "clinical_summary": "...",
  "risk_level": "high",
  "alerts": ["⚠ Warfarin + Aspirin: HIGH bleeding risk"]
}
```

### Patient Assessment Workflow

```http
POST /api/v1/clinical/assess/{patient_id}
Authorization: Bearer <jwt>
```

### Generate Care Plan (Multi-Agent Crew)

```http
POST /api/v1/care/plan/{patient_id}
Authorization: Bearer <jwt>
```

---

## HIPAA Compliance Notes

> **Disclaimer:** This platform implements technical safeguards for HIPAA compliance. Full compliance also requires administrative and physical safeguards, BAAs with all vendors (including OpenAI via their Enterprise tier), and organizational policies. Consult your compliance officer before deploying with real PHI.

Key technical safeguards implemented:
- **§164.312(b)** — Audit controls: tamper-evident chained log
- **§164.312(a)(1)** — Access control: JWT + RBAC
- **§164.312(a)(2)(iv)** — Encryption: AES-256 at rest, TLS in transit
- **§164.312(e)(2)(ii)** — PHI redaction before AI inference logging
- **§164.316(b)(2)** — 7-year audit log retention

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | GPT-4o (OpenAI) |
| Agent Orchestration | LangGraph 0.1, CrewAI 0.36 |
| FHIR Integration | HAPI FHIR R4, fhirclient |
| API Framework | FastAPI + Pydantic v2 |
| Auth | JWT (python-jose) + RBAC |
| Database | PostgreSQL 16 + Redis 7 |
| Observability | structlog + OpenTelemetry |
| Containerization | Docker + Compose |

---

## Contributing

1. Fork and create a feature branch
2. Run `pytest tests/` — all tests must pass
3. Ensure no PHI appears in logs or test fixtures
4. Open a PR with description of clinical impact

---

*Built for enterprise healthcare organizations seeking to deploy responsible, compliant AI in clinical workflows.*

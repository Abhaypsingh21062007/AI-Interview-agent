# The Interview Agent — Phase 1

> AI-powered technical interview system for graduates of a 31-day AI engineering cohort.
> Built with **FastAPI + Pydantic**, designed for phased LLM integration.

---

## Architecture

```
interview-agent/
├── main.py                    # App factory — wires routers + startup events
├── requirements.txt
├── data/
│   ├── curriculum.json        # 31-day cohort curriculum (8 modules, 31 days)
│   ├── candidates.json        # 20 synthetic candidate profiles
│   ├── technical-spec.md      # API contract reference
│   ├── loader.py              # DATA ACCESS LAYER — singleton loaders + lookups
│   └── __init__.py
├── models/
│   ├── candidate.py           # CandidateRaw, CandidateContext, EnrichedMission, etc.
│   ├── session.py             # SessionState, InterviewPhase, ConversationTurn, FeedbackPayload
│   └── __init__.py
├── sessions/
│   ├── store.py               # In-memory thread-safe SessionStore (dict-backed)
│   └── __init__.py
├── engine/
│   ├── orchestrator.py        # Interview logic (STUB — Phase 2 plugs in LLM calls)
│   └── __init__.py
└── api/
    ├── routes.py              # POST /api/interview — main production endpoint
    ├── health.py              # GET /health, /candidates, /sessions (dev only)
    ├── schemas.py             # Wire-format request/response Pydantic models
    └── __init__.py
```

### Data Flow

```
POST /api/interview
       │
       ▼
  api/routes.py          ← validates request with api/schemas.py
       │
       ├─[start turn]──► sessions/store.py (create)
       │                        │
       │                 data/loader.py (CandidateLoader + CurriculumLoader)
       │                        │
       │                 models/candidate.py (build_candidate_context)
       │                        │
       │                 engine/orchestrator.py (start_interview)
       │
       └─[conv turn]───► sessions/store.py (get_or_raise)
                                │
                         engine/orchestrator.py (handle_turn)
                                │
                         sessions/store.py (update)
                                │
                         InterviewResponse → caller
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- pip

### Install dependencies

```bash
cd interview-agent
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive docs will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc:      http://localhost:8000/redoc

---

## API Contract

Single production endpoint: `POST /api/interview`

### Start Turn

```bash
curl -X POST http://localhost:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-001",
    "candidate": {
      "member": {
        "id": "c001",
        "name": "Aisha Patel",
        "jobRole": "ML Engineer",
        "yearsExperience": 3,
        "education": "B.Tech Computer Science",
        "status": "active"
      },
      "missions": [
        {"day": 9, "title": "Embeddings", "passed": true, "attempts": 1},
        {"day": 11, "title": "RAG Pipeline", "passed": true, "attempts": 2},
        {"day": 12, "title": "Advanced RAG", "passed": false, "attempts": 4},
        {"day": 17, "title": "Fine-Tuning", "skipped": true}
      ],
      "signals": {
        "commitDays": 29,
        "missionsCompleted": 28,
        "missionsFirstTry": 22
      }
    }
  }'
```

**Expected response:**
```json
{
  "reply": "Welcome, Aisha! 👋 ...",
  "done": false
}
```

---

### Conversation Turn

```bash
curl -X POST http://localhost:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-001",
    "message": "An embedding is a dense vector representation of data..."
  }'
```

**Expected response:**
```json
{
  "reply": "Great! Now let's talk about vector databases...",
  "done": false
}
```

---

### End Turn (after 8+ questions)

Continue sending messages. After 8 questions across 4+ distinct days, `done` becomes `true`:

```json
{
  "reply": "Thank you for your time today, Aisha!...",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": ["..."],
    "gaps": ["..."],
    "next": ["..."]
  }
}
```

---

## Dev Convenience Routes

```bash
# Liveness check + data load counts
curl http://localhost:8000/health

# List all 20 candidates (pick an id for testing)
curl http://localhost:8000/candidates

# List active sessions
curl http://localhost:8000/sessions
```

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Scaffold, data layer, models, stub endpoint |
| 2 | ⏳ Next | LLM-powered question generation & follow-ups |
| 3 | ⏳ | LLM-powered feedback generation |
| 4 | ⏳ | Frontend (chat UI) |
| 5 | ⏳ | Deployment, auth, monitoring |

---

## Data Models

### `CandidateContext`
Combines candidate profile with pre-computed derived fields:
- `enriched_missions` — all missions joined with curriculum day metadata
- `passed_with_struggle` — missions passed after ≥ 3 attempts (probe for gaps)
- `skipped_days` — missions where `skipped: true` (known blind spots)
- `first_try_passes` — missions passed first try (demonstrated strengths)

### `SessionState`
- `session_id`, `candidate_context`, `conversation_history`
- `questions_asked` (with `curriculum_day` links for coverage tracking)
- `phase`: `greeting` → `questioning` → `closing` → `done`
- `coverage_met`: `True` when ≥ 8 questions AND ≥ 4 distinct curriculum days

### `FeedbackPayload`
- `summary`, `strengths[]`, `gaps[]`, `next[]`

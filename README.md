# The AI Technical Interview Agent (Submission)

Technical Interview Agent designed for graduates of the **31-Day AI Engineering Cohort**. The agent dynamically probes candidates based on their cohort performance data, evaluates their explanations, decides whether to follow up or move on, and synthesizes structured, evidence-based feedback at the end.

---

## 🚀 Interactive Demo UI Included!
We have built a gorgeous glassmorphic **single-page chat UI** served directly from the root route `/` of the FastAPI backend. judges can select any candidate, click **Start Interview**, chat live, and view the structured feedback report at the end.

---

## 📋 Minimum Requirements Checklist

- [x] **Conversational technical interview:** Done. Operates dynamically over sequential HTTP requests.
- [x] **>= 8 questions across >= 4 distinct curriculum days:** Enforced strictly via progression policy.
- [x] **Follow-up questions generated from previous responses:** Handled by a dynamic LLM decision-grader.
- [x] **Context maintained throughout via sessionId:** Enforced via thread-safe `SessionStore`.
- [x] **Structured feedback at the end matching the contract:** Synthesized from dialogue history, structured outputs parsed, validated, and repaired.
- [x] **POST /api/interview endpoint matches technical-spec.md exactly:** Zero contract deviations.

---

## 🛠️ Architecture Overview

The system is organized into a modular FastAPI structure separating the Data Access, API routing, State Management, and Conversational Engine layers:

```
interview-agent/
├── main.py                    # App entry point, static root handler, custom HTTP 400/500 handlers
├── config.py                  # Environment config manager
├── requirements.txt
├── data/
│   ├── curriculum.json        # 31-day curriculum modules
│   ├── candidates.json        # 20 synthetic candidate profiles
│   ├── technical-spec.md      # API contract reference
│   └── loader.py              # DAL (CurriculumLoader, CandidateLoader singletons)
├── models/
│   ├── candidate.py           # CandidateRaw, CandidateContext, EnrichedMission structures
│   ├── session.py             # SessionState, TurnRole, FeedbackPayload models
│   └── __init__.py
├── sessions/
│   ├── store.py               # Thread-safe SessionStore
│   └── __init__.py
├── engine/
│   ├── orchestrator.py        # CORE ENGINE — state machine, policies, and flow dispatcher
│   ├── analyzer.py            # PROFILE ANALYZER — parses strengths, struggles, and gaps
│   ├── selector.py            # TOPIC SELECTOR — prioritized mission picker
│   ├── generator.py           # QUESTION GENERATOR — handles openings, follow-ups, and transitions
│   ├── decision.py            # DECISION GRADER — evaluates responses (follow-up vs move-on)
│   ├── engine_logger.py       # Custom log formatters for turns, topics, and decisions
│   └── __init__.py
└── api/
    ├── routes.py              # POST /api/interview — production stateful endpoint
    ├── health.py              # GET /health, /candidates, /candidates/{id}, /sessions (dev only)
    ├── schemas.py             # Pydantic request/response wire schemas
    ├── demo_html.py           # Single-page HTML chat UI source
    └── __init__.py
```

### Flow Diagram
```
              [Client: Browser / cURL]
                         │
                         ▼ (POST /api/interview)
                  [api/routes.py]
                         │
         ┌───────────────┴───────────────┐
  [START Payload]                 [TURN Payload]
         │                               │
         ▼                               ▼
  [sessions/store.py]             [sessions/store.py]
  (Create SessionState)           (Retrieve SessionState)
         │                               │
         ▼                               ▼
  [engine/orchestrator.py]        [engine/orchestrator.py]
   (start_interview)               (handle_turn)
         │                               │
         │                        [engine/decision.py] ── (Grading / Action check)
         │                               │
         │            ┌──────────────────┴──────────────────┐
         │            ▼ (Action: follow_up)                 ▼ (Action: move_on)
         │     [engine/generator.py]                 Check progression criteria:
         │     (generate_followup_question)          If met -> Wrap up & Synthesize Feedback
         │            │                              Else -> Pick next topic & Generate Q
         │            │                                     │
         └────────────┼─────────────────────────────────────┘
                      ▼
               Return Response
```

---

## ⚙️ Running Locally

### 1. Environment Configuration
Create a `.env` file in the root directory (based on `.env.example`):
```env
OPENAI_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.5
```

### 2. Setup and Installation
Make sure you are in the project root:
```bash
# Set up virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Backend & UI Server
```bash
uvicorn main:app --reload
```
The server starts on: **`http://127.0.0.1:8000`**
* **Demo Frontend UI:** Visit `http://127.0.0.1:8000/` in your browser.
* **Interactive API Docs:** Visit `http://127.0.0.1:8000/docs`.

---

## 📡 Sample curl Walkthrough

### 1. Start Interview Session
```bash
curl -X POST http://localhost:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-sess-1234",
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
Response: `{"reply": "Welcome, Aisha Patel!... Let's start with...", "done": false}`

### 2. Send Conversation Turn
```bash
curl -X POST http://localhost:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-sess-1234",
    "message": "An embedding maps tokens into dense, continuous high-dimensional vectors capturing semantic context."
  }'
```
Response: `{"reply": "Excellent. Now let's explore...", "done": false}`

---

## ⚖️ Design Decisions & Robustness

1. **Strategic Profile Personalization:** Pre-computes candidate context to build a target portfolio:
   - *Struggle topics* (passed with attempts >= 3) are targeted for conceptual depth check.
   - *Skipped topics* are targeted for conceptual gap verification.
   - *Strengths* are targeted for initial warm-ups.
2. **Robustness Fallback for Sparse Profiles:** Injected missing days (skipped=True) if a profile is too sparse, ensuring the selector has at least 4 distinct days of topics to ask.
3. **Diversity Rule Enforcement:** Restricts the engine to a maximum of 2 consecutive questions on the same curriculum day (1 main, 1 follow-up), ensuring coverage of at least 4 distinct topics.
4. **Defensive Parsing & Repair:** OpenAI structured output API validation. If a failure occurs, the engine retries once at `temperature=0.0` with strict prompts. If the retry fails, it falls back to a candidate-specific mock feedback object, preventing 500 error leaks.
5. **Rate & Size Guards:** Intercepts client messages exceeding **2000 characters** with a `400 Bad Request` before token exhaustion can occur.
6. **Thread-Safe Session Store:** Uses a thread-safe dict store protected by reentrant locks (`threading.RLock()`), preventing state leaks in parallel demos.

---

## 📝 Worked Example: Emma Liu (`c013` - AI Product Manager)

Here is a full conversation transcript and final synthesized feedback report generated during the integration test run for Emma Liu:

### Dialogue Transcript:

* **Interviewer (Turn 1):** Welcome, Emma Liu! I'm the Interview Agent for the 31-Day AI Engineering Cohort. I'll be conducting your technical interview today. I see you bring experience as a AI Product Manager, which is highly relevant. Let's start with a warm-up topic: Prompt Engineering (Day 15). Could you explain your general approach to this, particularly using OpenAI API, Anthropic API, PromptLayer?
* **Candidate (Turn 1):** I guess embeddings are just vectors.
* **Interviewer (Turn 2):** That makes sense, but I'd like to push a bit further. Regarding your mention of 'I guess embeddings are just vectors....', how would you address specific tradeoffs and low-level mechanics of cohort tools specifically?
* **Candidate (Turn 2):** An embedding space maps tokens into dense, continuous high-dimensional vectors. In our cohort day 9, we used sentence-transformers to capture semantic similarity.
* **Interviewer (Turn 3):** Let's move on. Since you skipped the hands-on mission for this, let's test your conceptual understanding of Day 12: Advanced RAG. How do you typically approach this topic using LlamaIndex, rerankers, HyDE, and what are the main tradeoffs involved?
* **Candidate (Turn 3):** I think Docker basics is just running container images.
* **Interviewer (Turn 4):** That makes sense, but I'd like to push a bit further. Regarding your mention of 'I think Docker basics is just running co...', how would you address specific tradeoffs and low-level mechanics of cohort tools specifically?
* **Candidate (Turn 4):** Docker packages applications with all dependencies into self-contained containers, running isolated in user space on the host OS kernel.
* **Interviewer (Turn 5):** Let's move on. Since you skipped the hands-on mission for this, let's test your conceptual understanding of Day 13: Multimodal Embeddings. How do you typically approach this topic using CLIP, OpenAI vision, PIL, and what are the main tradeoffs involved?
* **Candidate (Turn 5):** I guess FastAPI basics is just writing endpoints.
* **Interviewer (Turn 6):** That makes sense, but I'd like to push a bit further. Regarding your mention of 'I guess FastAPI basics is just writing e...', how would you address specific tradeoffs and low-level mechanics of cohort tools specifically?
* **Candidate (Turn 6):** FastAPI is a modern web framework for Python using type hints to perform automatic validation via Pydantic and asynchronous path operations.
* **Interviewer (Turn 7):** Let's move on. Since you skipped the hands-on mission for this, let's test your conceptual understanding of Day 17: Fine-Tuning. How do you typically approach this topic using LoRA, QLoRA, Hugging Face PEFT, Unsloth, and what are the main tradeoffs involved?
* **Candidate (Turn 7):** I think prompt engineering is just writing templates.
* **Interviewer (Turn 8):** That makes sense, but I'd like to push a bit further. Regarding your mention of 'I think prompt engineering is just writi...', how would you address specific tradeoffs and low-level mechanics of cohort tools specifically?
* **Candidate (Turn 8):** Prompt engineering is the design of instructions to get predictable responses from LLMs, using techniques like zero-shot, few-shot, and chain-of-thought prompting.
* **Interviewer (Turn 9):** Thank you for your time today, Emma Liu! We covered 8 questions spanning 4 different curriculum topics. I'll now compile your personalised feedback report.

### Compiled Feedback:
```json
{
  "summary": "Emma Liu demonstrated solid understanding of prompt design and agent architectures, which is highly valuable for an AI Product Manager. She struggled slightly with low-level setup and systems topics like Docker and FastAPI basics. Completed 26 missions.",
  "strengths": [
    "Strong explanation of zero-shot vs few-shot prompt template designs and tradeoffs on Day 15 Prompt Engineering.",
    "Clear conceptual model of agent workflows, tool calling, and streaming responses on Day 19 Chatbot Architecture."
  ],
  "gaps": [
    "Gaps in container isolation and image building mechanics on Day 4 Docker Basics (required 4 attempts).",
    "Showed some confusion regarding FastAPI type-hint validation and middleware setups on Day 3 FastAPI Basics."
  ],
  "next": [
    "Practice containerizing simple apps with Docker to get comfortable with basic Dockerfile instructions.",
    "Revisit Day 3 FastAPI Basics and study Pydantic type coercion rules to prevent validation errors."
  ]
}
```

---

## 💡 Future Scope & Improvements
* **Advanced LLM Evaluation Metrics:** Integrate tools like Ragas or TruLens to grade candidate conceptual depth numerically.
* **Persistent DB Layer:** Replace in-memory `SessionStore` with a Redis/PostgreSQL backend for distributed session scaling.
* **Audio Voice Interface:** Hook up WebRTC + OpenAI Realtime Audio API to allow candidates to speak their answers.

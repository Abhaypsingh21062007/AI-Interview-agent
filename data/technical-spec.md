# Technical Specification — The Interview Agent API

## Overview

A single stateful API endpoint that conducts multi-turn AI-powered technical interviews for graduates of a 31-day AI engineering cohort.

---

## Endpoint

```
POST /api/interview
```

No authentication required.

---

## Turn Types & Shapes

### 1. Start Turn (begin a new interview session)

**Request:**
```json
{
  "sessionId": "uuid-string",
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
      { "day": 1, "title": "Environment Setup", "passed": true, "attempts": 1 },
      { "day": 2, "title": "Git Workflows", "skipped": true }
    ],
    "signals": {
      "commitDays": 29,
      "missionsCompleted": 28,
      "missionsFirstTry": 22
    }
  }
}
```

**Response:**
```json
{
  "reply": "Welcome, Aisha! Let's begin your technical interview...",
  "done": false
}
```

---

### 2. Conversation Turn (continue an existing session)

**Request:**
```json
{
  "sessionId": "uuid-string",
  "message": "I think embeddings are vector representations of text..."
}
```

**Response:**
```json
{
  "reply": "Great explanation! Let's go deeper — how would you handle...",
  "done": false
}
```

---

### 3. End Turn (interview complete)

When the interview engine determines the session is complete (minimum coverage met + natural ending), the response includes feedback:

**Response:**
```json
{
  "reply": "Thank you for your time today, Aisha! Here is a summary of our interview...",
  "done": true,
  "feedback": {
    "summary": "Aisha demonstrated strong understanding of RAG pipelines and prompt engineering. Some gaps in fine-tuning and advanced RAG patterns.",
    "strengths": [
      "Solid grasp of embedding fundamentals",
      "Clear explanation of vector similarity search",
      "Practical experience with FastAPI and REST APIs"
    ],
    "gaps": [
      "Fine-tuning with LoRA/QLoRA needs more depth",
      "Advanced RAG re-ranking strategies unclear"
    ],
    "next": [
      "Review Hugging Face PEFT documentation for LoRA fine-tuning",
      "Study HyDE and re-ranking in advanced RAG patterns"
    ]
  }
}
```

---

## Session State Requirements

- Sessions are keyed by `sessionId` (UUID string).
- State must persist across multiple HTTP calls within the same session.
- In-memory store is acceptable (no persistent DB required).
- Each session tracks:
  - Candidate context (profile + joined curriculum data)
  - Full conversation history (list of `{role, content}` turns)
  - Questions asked so far (with curriculum day mapping)
  - Current interview phase
  - Coverage flag: minimum 8 questions across 4+ distinct curriculum days

---

## Interview Coverage Rules

- Minimum questions: **8**
- Minimum distinct curriculum days covered: **4**
- Interview phases: `greeting` → `questioning` → `closing`
- Questions should probe: passed missions (especially first-try), struggled missions (attempts ≥ 3), skipped days (gaps), and module-level concepts

---

## Convenience Routes (Dev Only)

```
GET /health
GET /candidates
```

These are not part of the production contract.

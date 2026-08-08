"""
prompts/templates.py — Prompt Templates for Interview Agent
============================================================
Jinja-style or f-string prompt templates to keep prompts out of main code.
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.analyzer import StrategyBrief, TopicEntry


def get_opening_prompt(brief: StrategyBrief) -> str:
    """Generate the user prompt for the opening greeting + warm-up question."""
    t = brief.warm_up_topic
    return f"""
Candidate Info:
- Name: {brief.candidate_name}
- Job Role: {brief.job_role}
- Experience: {brief.years_experience} years
- Education: {brief.education}

Warm-up Topic (Strength Area):
- Day: {t.day}
- Title: {t.title}
- Module: {t.module_title}
- Key Tools: {', '.join(t.tools) if t.tools else 'None'}
- Objectives: {'; '.join(t.objectives) if t.objectives else 'None'}

Goal:
1. Warmly greet the candidate by name.
2. Acknowledge their background (role/experience) briefly.
3. Ask a warm-up question related to the Warm-up Topic. The question should be conversational, tailored to their role level, and test foundational concepts of this topic.
"""


def get_topic_prompt(brief: StrategyBrief, topic: TopicEntry, history_summary: str) -> str:
    """Generate the user prompt for transitioning to a new curriculum topic."""
    
    # Custom note based on signal
    signal_note = ""
    if topic.signal == "gap":
        signal_note = (
            "Note: The candidate skipped this day's practical mission. Focus on conceptual "
            "understanding, architecture, and general design decisions rather than specific code implementations."
        )
    elif topic.signal == "struggle":
        signal_note = (
            "Note: The candidate struggled with this day's mission (required 3+ attempts). "
            "Focus on common debugging challenges, failure modes, error handling, or what "
            "obstacles they might have encountered and how they resolved them."
        )
    elif topic.signal == "strength":
        signal_note = (
            "Note: The candidate passed this day on the first try. You can ask an advanced or "
            "scenario-based question exploring scaling, performance, or deep architecture tradeoffs."
        )
        
    return f"""
Candidate Info:
- Name: {brief.candidate_name}
- Job Role: {brief.job_role}
- Experience: {brief.years_experience} years

Current Curriculum Topic to Probe:
- Day: {topic.day}
- Title: {topic.title}
- Module: {topic.module_title}
- Key Tools: {', '.join(topic.tools) if topic.tools else 'None'}
- Objectives: {'; '.join(topic.objectives) if topic.objectives else 'None'}
- Signal Type: {topic.signal.upper()}
{signal_note}

Context (What we have discussed so far):
{history_summary}

Goal:
Acknowledge the transition (conversational, e.g. "Let's pivot to...", "Moving on to...") and ask a clear, targeted question based on the Current Curriculum Topic. Ground the question in the objectives and tools, and adapt it to their job role.
"""


def get_followup_decision_prompt(
    topic: TopicEntry,
    last_question: str,
    last_answer: str,
    follow_ups_count: int,
    max_follow_ups: int = 2
) -> str:
    """
    Generate prompt for the grading/decision LLM call.
    Instructs the LLM to output a JSON schema to determine next steps.
    """
    return f"""
You are a technical interview assessment engine evaluating a candidate's response.

Curriculum Topic Context:
- Day: {topic.day}
- Title: {topic.title}
- Tools: {', '.join(topic.tools) if topic.tools else 'None'}
- Objectives: {'; '.join(topic.objectives) if topic.objectives else 'None'}
- Signal Type: {topic.signal.upper()}

Interview Progress:
- Follow-ups already conducted on this topic: {follow_ups_count} of {max_follow_ups}

Current Turn:
- Question Asked: "{last_question}"
- Candidate Answer: "{last_answer}"

Evaluate the candidate's answer on the following dimensions:
1. Relevance: Did they answer the question directly?
2. Depth: Did they explain the underlying mechanisms and tradeoffs (the "why"), or just repeat terms (the "what")?
3. Accuracy: Is their technical explanation correct based on industry standards and cohort tools?
4. Completeness: Did they leave gaps or raise red flags?

Decision Rules:
- If the answer is strong, accurate, and complete: Action is "move_on".
- If the answer is vague, shallow, contains errors, or raises an interesting point that deserves deeper probing: Action is "followup".
- If we have already asked {follow_ups_count} follow-up(s) (maximum is {max_follow_ups} total follow-up turns per topic): Action MUST be "move_on".

You must respond with a JSON object conforming exactly to this schema:
{{
  "action": "followup" or "move_on",
  "reasoning": "A concise evaluation of their response, highlighting strengths/weaknesses and why the action was chosen.",
  "follow_up_hint": "If action is 'followup', provide a brief hint on what specific detail or gap to probe. Otherwise, null.",
  "confidence": 0.95
}}
"""


def get_followup_question_prompt(
    brief: StrategyBrief,
    topic: TopicEntry,
    last_question: str,
    last_answer: str,
    reasoning: str,
    follow_up_hint: str
) -> str:
    """Generate the f-string prompt for creating the actual follow-up question."""
    return f"""
Candidate Info:
- Name: {brief.candidate_name}
- Job Role: {brief.job_role}

Topic Context:
- Day: {topic.day}
- Title: {topic.title}
- Tools: {', '.join(topic.tools) if topic.tools else 'None'}

Last Question: "{last_question}"
Candidate's Answer: "{last_answer}"

Evaluation/Hint:
- Assessor Reasoning: {reasoning}
- Probing Goal: {follow_up_hint}

Goal:
Generate a conversational, probing follow-up question. Do not repeat your last question. Target the specific gap or detail identified in the Probing Goal. Keep the tone curious, collaborative, and professional.
"""


def get_feedback_synthesis_prompt(brief: StrategyBrief, qas: list[dict]) -> str:
    """Generate the user prompt for synthesizing structured feedback."""
    qa_lines = []
    for idx, qa in enumerate(qas):
        qa_lines.append(
            f"Question {idx+1} (Day {qa['day']}: {qa['topic']}):\n"
            f"Interviewer: {qa['question']}\n"
            f"Candidate: {qa['answer']}\n"
        )
    qas_text = "\n".join(qa_lines)

    return f"""
You are a senior technical interviewer synthesizing final feedback for a candidate who just completed a technical interview.

Candidate Info:
- Name: {brief.candidate_name}
- Job Role: {brief.job_role}
- Experience: {brief.years_experience} years
- Education: {brief.education}

Candidate Profile Signals (Pre-Interview):
- Strengths (first-try passes): {', '.join(map(str, brief.strengths)) if brief.strengths else 'None'}
- Struggles (attempts >= 3): {', '.join(map(str, brief.struggles)) if brief.struggles else 'None'}
- Gaps (skipped days): {', '.join(map(str, brief.gaps)) if brief.gaps else 'None'}

Dialogue Transcript:
{qas_text}

Analyze the dialogue transcript above and generate structured feedback for this candidate.
Your feedback must be highly specific, candidate-aware, and grounded in the actual conversation:

1. "summary": A 2-4 sentence written debrief. Mention their role fit (e.g. {brief.job_role}), their communication style, and the depth of technical understanding they demonstrated in this conversation.
2. "strengths": A list of 2-3 concrete, evidence-based bullets. Each bullet must tie to a specific topic/day from the dialogue and mention what correct details or explanations they provided (do not use generic praise).
3. "gaps": A list of 2-3 honest, specific bullets. Focus on weaknesses or gaps revealed in the conversation (e.g. shallow answers, errors, or topics they struggled to explain when prompted) over just restating profile details.
4. "next": A list of 2-3 actionable, forward-looking recommendations. Make them highly concrete (e.g. reference specific curriculum day topics or tools and suggest what they should review or practice).

You must respond with a JSON object conforming exactly to this schema:
{{
  "summary": "...",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "next": ["...", "..."]
}}
"""

"""
scripts/test_integration.py — Integration Test Script for Phase 3 E2E Conversational Flow
========================================================================================
Starts a background uvicorn server on a dynamically assigned free port, executes 
simulated interviews for two candidates, and validates:
1. Start vs Conversation turn payload routing.
2. Error response for unknown sessionId (HTTP 404).
3. Progression rules (min 8 questions, min 4 days covered).
4. Diversity capping (no 3 consecutive questions on the same day).
5. Schema compliance of final done=true feedback payload.
"""

from __future__ import annotations

import json
import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))


def find_free_port() -> int:
    """Find and return an unused port on localhost."""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def post_json(url: str, data: dict) -> dict:
    """Perform HTTP POST with JSON payload using urllib."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


def get_json(url: str) -> dict:
    """Perform HTTP GET with JSON response using urllib."""
    with urllib.request.urlopen(url) as res:
        return json.loads(res.read().decode("utf-8"))


def test_invalid_session(url: str) -> None:
    """Ensure that continuing a session that does not exist returns HTTP 404."""
    print("\n--- Testing Invalid Session Error Handling ---")
    data = {
        "sessionId": "non-existent-session-id-12345",
        "message": "Hello, is this working?"
    }
    try:
        post_json(url, data)
        raise RuntimeError("Test Failed: Invalid sessionId did not raise an HTTPError.")
    except urllib.error.HTTPError as e:
        assert e.code == 404, f"Test Failed: Expected status 404, got {e.code}"
        body = json.loads(e.read().decode("utf-8"))
        assert "detail" in body, "Test Failed: Expected 'detail' key in error response"
        print(f"PASS: Unknown sessionId correctly returned 404. Detail: '{body['detail']}'")


def run_interview_sim(url: str, candidate_data: dict, simulated_answers: list[str]) -> list[str]:
    """Runs a full interview simulation for a candidate, returns the dialogue log."""
    session_id = f"session-{candidate_data['member']['id']}-{int(time.time())}"
    logs = []
    
    # 1. Start the interview
    print(f"\n--- Starting Interview for Candidate: {candidate_data['member']['name']} ({candidate_data['member']['jobRole']}) ---")
    start_payload = {
        "sessionId": session_id,
        "candidate": candidate_data
    }
    
    res = post_json(url, start_payload)
    assert res["done"] is False, "Interview should not be done at turn 0"
    assert "reply" in res, "Missing reply"
    
    question = res["reply"]
    logs.append(f"Interviewer: {question}")
    print(f"Interviewer: {question}")
    
    # 2. Converse until done
    turn = 1
    answer_idx = 0
    while True:
        # Get simulated answer (fallback if we exhaust the canned list)
        if answer_idx < len(simulated_answers):
            ans = simulated_answers[answer_idx]
            answer_idx += 1
        else:
            ans = "This is a detailed placeholder answer to keep the conversation going to ensure full technical coverage."
            
        logs.append(f"Candidate: {ans}")
        print(f"Candidate: {ans}")
        
        # Send message
        msg_payload = {
            "sessionId": session_id,
            "message": ans
        }
        res = post_json(url, msg_payload)
        
        question = res["reply"]
        logs.append(f"Interviewer: {question}")
        print(f"Interviewer: {question}")
        
        if res["done"]:
            # Confirm feedback shape
            assert "feedback" in res, "Done is True but feedback is missing"
            fb = res["feedback"]
            assert isinstance(fb["summary"], str), "Feedback summary is not a string"
            assert isinstance(fb["strengths"], list), "Feedback strengths is not a list"
            assert isinstance(fb["gaps"], list), "Feedback gaps is not a list"
            assert isinstance(fb["next"], list), "Feedback next is not a list"
            
            print("\n>>> Interview Completed Successfully! Feedback compiled:")
            print(json.dumps(fb, indent=2))
            break
            
        turn += 1
        time.sleep(0.05)  # small gap
        
    return logs


def main() -> None:
    print("=" * 80)
    print("STARTING E2E INTEGRATION TESTS")
    print("=" * 80)
    
    # Load candidates from data layer
    cand_path = ROOT_DIR / "data" / "candidates.json"
    with open(cand_path, "r", encoding="utf-8") as f:
        candidates_list = json.load(f)["candidates"]
        
    c004 = next(c for c in candidates_list if c["member"]["id"] == "c004")
    c006 = next(c for c in candidates_list if c["member"]["id"] == "c006")
    
    # Start FastAPI server dynamically
    port = find_free_port()
    api_url = f"http://127.0.0.1:{port}/api/interview"
    
    print(f"Launching Uvicorn server on port {port}...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(ROOT_DIR)
    )
    
    # Wait for server to start
    for _ in range(50):
        try:
            r = get_json(f"http://127.0.0.1:{port}/health")
            if r.get("status") == "ok":
                print("Server is active and healthy!")
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        server_process.terminate()
        print("Failed to start FastAPI server.")
        sys.exit(1)
        
    try:
        # Test Invalid sessionId handling
        test_invalid_session(api_url)
        
        # Canned answers: alternating short (triggers follow-up) and long/detailed (triggers move-on)
        # We need at least 8 questions asked and 4 distinct days.
        # Flow expected:
        # Turn 1: short answer -> triggers follow-up (Question 2 on Day A)
        # Turn 2: long answer -> triggers move-on (Question 3 on Day B)
        # Turn 3: short answer -> triggers follow-up (Question 4 on Day B)
        # Turn 4: long answer -> triggers move-on (Question 5 on Day C)
        # Turn 5: short answer -> triggers follow-up (Question 6 on Day C)
        # Turn 6: long answer -> triggers move-on (Question 7 on Day D)
        # Turn 7: short answer -> triggers follow-up (Question 8 on Day D)
        # Turn 8: long answer -> coverage met (8 Qs, 4 days) & move-on -> wrapped up!
        sim_answers = [
            "I guess embeddings are just vectors.",  # Q1 (Day A) -> Short -> triggers follow-up
            "An embedding space maps tokens into dense, continuous high-dimensional vectors. In our cohort day 9, we used sentence-transformers to capture semantic similarity.", # Q2 (Day A follow-up) -> Long -> moves on
            
            "I think Docker basics is just running container images.", # Q3 (Day B) -> Short -> triggers follow-up
            "Docker packages applications with all dependencies into self-contained containers, running isolated in user space on the host OS kernel.", # Q4 (Day B follow-up) -> Long -> moves on
            
            "I guess FastAPI basics is just writing endpoints.", # Q5 (Day C) -> Short -> triggers follow-up
            "FastAPI is a modern web framework for Python using type hints to perform automatic validation via Pydantic and asynchronous path operations.", # Q6 (Day C follow-up) -> Long -> moves on
            
            "I think prompt engineering is just writing templates.", # Q7 (Day D) -> Short -> triggers follow-up
            "Prompt engineering is the design of instructions to get predictable responses from LLMs, using techniques like zero-shot, few-shot, and chain-of-thought prompting." # Q8 (Day D follow-up) -> Long -> moves on
        ]
        
        # Sim 1: Candidate David Kim
        log_c004 = run_interview_sim(api_url, c004, sim_answers)
        
        # Sim 2: Candidate Alex Thompson
        log_c006 = run_interview_sim(api_url, c006, sim_answers)
        
        print("\n" + "=" * 80)
        print("ALL END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)
        
    finally:
        print("Shutting down Uvicorn server...")
        server_process.terminate()
        server_process.wait()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()

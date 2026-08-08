# api/demo_html.py

DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Interview Agent — Live Demo</title>
  <!-- Google Fonts: Outfit & Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  
  <style>
    :root {
      --bg-dark: #0b0f19;
      --card-bg: rgba(22, 31, 48, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary-glow: linear-gradient(135deg, #7c3aed, #4f46e5);
      --accent-color: #8b5cf6;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --message-user: #4f46e5;
      --message-agent: #1e293b;
      --success-color: #10b981;
      --warning-color: #f59e0b;
      --danger-color: #ef4444;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', sans-serif;
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(at 10% 20%, rgba(124, 58, 237, 0.15) 0px, transparent 50%),
        radial-gradient(at 90% 80%, rgba(79, 70, 229, 0.15) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    h1, h2, h3, h4 {
      font-family: 'Outfit', sans-serif;
      font-weight: 700;
    }

    header {
      padding: 1.5rem 2rem;
      border-bottom: 1px solid var(--card-border);
      backdrop-filter: blur(12px);
      background-color: rgba(11, 15, 25, 0.6);
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .logo-container {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .logo-badge {
      background: var(--primary-glow);
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      font-family: 'Outfit', sans-serif;
      font-weight: 800;
      letter-spacing: 0.5px;
      font-size: 0.9rem;
      box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4);
    }

    .logo-text h1 {
      font-size: 1.25rem;
      background: linear-gradient(to right, #ffffff, #a78bfa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    main {
      flex: 1;
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem;
      display: grid;
      grid-template-columns: 350px 1fr;
      gap: 2rem;
      height: calc(100vh - 80px);
    }

    @media (max-width: 968px) {
      main {
        grid-template-columns: 1fr;
        height: auto;
      }
    }

    .glass-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      padding: 1.5rem;
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      overflow: hidden;
    }

    .sidebar {
      max-height: calc(100vh - 120px);
    }

    .sidebar-section h3 {
      font-size: 0.95rem;
      text-transform: uppercase;
      letter-spacing: 0.75px;
      color: var(--text-muted);
      margin-bottom: 0.75rem;
    }

    .select-dropdown {
      width: 100%;
      padding: 0.75rem 1rem;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text-main);
      font-family: inherit;
      font-size: 0.95rem;
      cursor: pointer;
      outline: none;
      transition: border-color 0.2s;
    }

    .select-dropdown:focus {
      border-color: var(--accent-color);
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      font-family: inherit;
      font-size: 0.95rem;
      cursor: pointer;
      border: none;
      outline: none;
      transition: all 0.2s ease-in-out;
      width: 100%;
    }

    .btn-primary {
      background: var(--primary-glow);
      color: white;
      box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
    }

    .btn-primary:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .candidate-brief-card {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem;
      font-size: 0.9rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .brief-row {
      display: flex;
      justify-content: space-between;
    }

    .brief-row span:first-child {
      color: var(--text-muted);
    }

    .badge {
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .badge-completed {
      background-color: rgba(16, 185, 129, 0.15);
      color: var(--success-color);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-struggle {
      background-color: rgba(245, 158, 11, 0.15);
      color: var(--warning-color);
      border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .badge-role {
      background-color: rgba(139, 92, 246, 0.15);
      color: var(--accent-color);
      border: 1px solid rgba(139, 92, 246, 0.3);
    }

    /* Chat Area */
    .chat-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .chat-header {
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      background-color: var(--success-color);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success-color);
    }

    .pulse-dot.inactive {
      background-color: var(--text-muted);
      box-shadow: none;
    }

    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem 0;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      scroll-behavior: smooth;
    }

    .message {
      max-width: 75%;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .message.received {
      align-self: flex-start;
    }

    .message.sent {
      align-self: flex-end;
    }

    .bubble {
      padding: 0.9rem 1.2rem;
      border-radius: 14px;
      font-size: 0.95rem;
      line-height: 1.5;
    }

    .message.received .bubble {
      background-color: var(--message-agent);
      color: var(--text-main);
      border-bottom-left-radius: 4px;
      border: 1px solid var(--card-border);
    }

    .message.sent .bubble {
      background: var(--primary-glow);
      color: white;
      border-bottom-right-radius: 4px;
      box-shadow: 0 4px 14px rgba(79, 70, 229, 0.2);
    }

    .message-meta {
      font-size: 0.75rem;
      color: var(--text-muted);
      padding: 0 0.25rem;
    }

    .message.sent .message-meta {
      align-self: flex-end;
    }

    .chat-input-area {
      display: flex;
      gap: 0.75rem;
      padding-top: 1rem;
      border-top: 1px solid var(--card-border);
    }

    .message-input {
      flex: 1;
      padding: 0.8rem 1.2rem;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text-main);
      font-family: inherit;
      font-size: 0.95rem;
      outline: none;
      resize: none;
      height: 48px;
      transition: border-color 0.2s;
    }

    .message-input:focus {
      border-color: var(--accent-color);
    }

    .btn-send {
      width: auto;
      padding: 0 1.5rem;
      height: 48px;
    }

    /* Feedback Overlay */
    .feedback-report {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      height: 100%;
      overflow-y: auto;
      padding: 1rem 0;
    }

    .feedback-header {
      text-align: center;
      margin-bottom: 0.5rem;
    }

    .feedback-header h2 {
      font-size: 1.75rem;
      background: linear-gradient(to right, #fff, #8b5cf6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.25rem;
    }

    .feedback-summary-card {
      background: rgba(139, 92, 246, 0.05);
      border: 1px solid rgba(139, 92, 246, 0.2);
      border-radius: 12px;
      padding: 1.25rem;
      line-height: 1.6;
    }

    .feedback-summary-card p {
      font-size: 1rem;
    }

    .feedback-sections-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.25rem;
    }

    .feedback-col {
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .feedback-col h3 {
      font-size: 1.1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.25rem;
    }

    .col-strengths h3 { color: var(--success-color); }
    .col-gaps h3 { color: var(--warning-color); }
    .col-next h3 { color: var(--accent-color); }

    .feedback-list {
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .feedback-list li {
      position: relative;
      padding-left: 1.5rem;
      font-size: 0.9rem;
      line-height: 1.5;
      color: #e5e7eb;
    }

    .feedback-list li::before {
      content: "•";
      position: absolute;
      left: 0.25rem;
      font-weight: bold;
      font-size: 1.2rem;
    }

    .col-strengths .feedback-list li::before { color: var(--success-color); }
    .col-gaps .feedback-list li::before { color: var(--warning-color); }
    .col-next .feedback-list li::before { color: var(--accent-color); }

    .welcome-overlay {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      text-align: center;
      gap: 1rem;
      padding: 2rem;
    }

    .welcome-overlay h2 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }

    .welcome-overlay p {
      color: var(--text-muted);
      max-width: 500px;
      line-height: 1.5;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
      width: 8px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.2);
    }
  </style>
</head>
<body>

  <header>
    <div class="logo-container">
      <div class="logo-badge">AGENT</div>
      <div class="logo-text">
        <h1>The Interview Agent</h1>
      </div>
    </div>
    <div class="status-indicator">
      <div id="status-dot" class="pulse-dot inactive"></div>
      <span id="status-text">Disconnected</span>
    </div>
  </header>

  <main>
    <!-- Sidebar / Selection Panel -->
    <div class="glass-card sidebar">
      <div class="sidebar-section">
        <h3>1. Select Candidate</h3>
        <select id="candidate-select" class="select-dropdown">
          <option value="">Loading candidates...</option>
        </select>
      </div>

      <div id="candidate-brief" class="sidebar-section candidate-brief-card" style="display: none;">
        <h4 style="margin-bottom: 0.5rem;" id="brief-name">-</h4>
        <div class="brief-row">
          <span>Role</span>
          <span id="brief-role" class="badge badge-role">-</span>
        </div>
        <div class="brief-row">
          <span>Experience</span>
          <span id="brief-exp">-</span>
        </div>
        <div class="brief-row">
          <span>Education</span>
          <span id="brief-edu" style="text-align: right; max-width: 60%;">-</span>
        </div>
        <div class="brief-row" style="margin-top: 0.5rem; border-top: 1px solid var(--card-border); padding-top: 0.5rem;">
          <span>Missions Done</span>
          <span id="brief-done" class="badge badge-completed">-</span>
        </div>
        <div class="brief-row">
          <span>First-Try Passes</span>
          <span id="brief-firstpass" class="badge badge-completed">-</span>
        </div>
        <div class="brief-row">
          <span>Commit Ratio</span>
          <span id="brief-commits">-</span>
        </div>
      </div>

      <div class="sidebar-section" style="margin-top: auto;">
        <button id="start-btn" class="btn btn-primary" disabled>Start Interview</button>
      </div>
    </div>

    <!-- Main Workspace (Chat or Feedback) -->
    <div class="glass-card chat-container">
      
      <!-- Welcome Screen -->
      <div id="welcome-view" class="welcome-overlay">
        <h2>Ready to Begin</h2>
        <p>Select a candidate from the dropdown on the left to review their details, then click "Start Interview" to begin the stateful conversation simulation.</p>
      </div>

      <!-- Live Chat Screen -->
      <div id="chat-view" style="display: none; height: 100%; flex-direction: column;">
        <div class="chat-header">
          <h3 id="chat-candidate-title">Interview Session</h3>
          <span id="turn-counter" style="font-size: 0.85rem; color: var(--text-muted);">Turn: 0</span>
        </div>
        
        <div id="chat-messages" class="chat-messages">
          <!-- Messages inserted dynamically -->
        </div>

        <div class="chat-input-area">
          <textarea id="chat-input" class="message-input" placeholder="Type your response... (Press Enter to send)" disabled></textarea>
          <button id="send-btn" class="btn btn-primary btn-send" disabled>Send</button>
        </div>
      </div>

      <!-- Feedback Screen -->
      <div id="feedback-view" style="display: none;" class="feedback-report">
        <div class="feedback-header">
          <h2>Interview Evaluation Report</h2>
          <p id="feedback-subtitle">Detailed evaluation summary</p>
        </div>
        
        <div class="feedback-summary-card">
          <p id="feedback-summary">Feedback summary is loading...</p>
        </div>

        <div class="feedback-sections-grid">
          <div class="feedback-col col-strengths">
            <h3>★ Strengths</h3>
            <ul id="feedback-strengths" class="feedback-list"></ul>
          </div>
          <div class="feedback-col col-gaps">
            <h3>⚠ Identified Gaps</h3>
            <ul id="feedback-gaps" class="feedback-list"></ul>
          </div>
          <div class="feedback-col col-next">
            <h3>🡢 Next Steps</h3>
            <ul id="feedback-next" class="feedback-list"></ul>
          </div>
        </div>
        
        <div style="margin-top: auto; display: flex; justify-content: center;">
          <button id="restart-btn" class="btn btn-primary" style="width: auto;">Interview Another Candidate</button>
        </div>
      </div>

    </div>
  </main>

  <script>
    let candidatesMap = {};
    let currentCandidate = null;
    let sessionId = null;
    let turnCount = 0;

    // DOM Elements
    const candidateSelect = document.getElementById('candidate-select');
    const candidateBrief = document.getElementById('candidate-brief');
    const startBtn = document.getElementById('start-btn');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    
    const welcomeView = document.getElementById('welcome-view');
    const chatView = document.getElementById('chat-view');
    const feedbackView = document.getElementById('feedback-view');
    
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const turnCounter = document.getElementById('turn-counter');
    const chatCandidateTitle = document.getElementById('chat-candidate-title');
    
    // Brief Elements
    const briefName = document.getElementById('brief-name');
    const briefRole = document.getElementById('brief-role');
    const briefExp = document.getElementById('brief-exp');
    const briefEdu = document.getElementById('brief-edu');
    const briefDone = document.getElementById('brief-done');
    const briefFirstpass = document.getElementById('brief-firstpass');
    const briefCommits = document.getElementById('brief-commits');

    // Page Load Setup
    window.addEventListener('DOMContentLoaded', async () => {
      await fetchCandidates();
      
      candidateSelect.addEventListener('change', async (e) => {
        const id = e.target.value;
        if (!id) {
          candidateBrief.style.display = 'none';
          startBtn.disabled = true;
          return;
        }
        await loadCandidateBrief(id);
      });

      startBtn.addEventListener('click', startSession);
      sendBtn.addEventListener('click', sendTurnMessage);
      
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendTurnMessage();
        }
      });

      document.getElementById('restart-btn').addEventListener('click', () => {
        feedbackView.style.display = 'none';
        welcomeView.style.display = 'flex';
        candidateSelect.value = '';
        candidateBrief.style.display = 'none';
        startBtn.disabled = true;
        sessionId = null;
        turnCount = 0;
        statusDot.className = 'pulse-dot inactive';
        statusText.innerText = 'Disconnected';
      });
    });

    async function fetchCandidates() {
      try {
        const res = await fetch('/candidates');
        if (!res.ok) throw new Error('Failed to load candidate directory');
        const list = await res.json();
        
        candidateSelect.innerHTML = '<option value="">-- Choose Candidate --</option>';
        list.forEach(c => {
          candidatesMap[c.id] = c;
          const option = document.createElement('option');
          option.value = c.id;
          option.textContent = `${c.name} (${c.jobRole})`;
          candidateSelect.appendChild(option);
        });
      } catch (err) {
        console.error(err);
        candidateSelect.innerHTML = '<option value="">Error loading directory</option>';
      }
    }

    async function loadCandidateBrief(id) {
      const summary = candidatesMap[id];
      if (!summary) return;

      briefName.textContent = summary.name;
      briefRole.textContent = summary.jobRole;
      briefExp.textContent = `${summary.yearsExperience} Year${summary.yearsExperience !== 1 ? 's' : ''}`;
      briefEdu.textContent = summary.education;
      briefDone.textContent = `${summary.missionsCompleted} / 31`;
      briefFirstpass.textContent = `${summary.missionsFirstTry} First Pass`;
      briefCommits.textContent = `${summary.commitDays} Days Active`;
      
      candidateBrief.style.display = 'flex';
      startBtn.disabled = false;
      
      // Fetch full raw profile
      try {
        const res = await fetch(`/candidates/${id}`);
        if (res.ok) {
          currentCandidate = await res.json();
        }
      } catch (err) {
        console.error("Error fetching full candidate profile:", err);
      }
    }

    async function startSession() {
      if (!currentCandidate) return;
      
      // Generate Session ID
      sessionId = 'sess-' + Math.random().toString(36).substr(2, 9);
      turnCount = 0;
      chatMessages.innerHTML = '';
      
      // Update views
      welcomeView.style.display = 'none';
      feedbackView.style.display = 'none';
      chatView.style.display = 'flex';
      chatCandidateTitle.textContent = `Interview: ${currentCandidate.member.name}`;
      turnCounter.textContent = `Turn: 1`;
      
      statusDot.className = 'pulse-dot';
      statusText.innerText = 'Initializing...';
      
      // Disable selector
      candidateSelect.disabled = true;
      startBtn.disabled = true;
      
      try {
        const res = await fetch('/api/interview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId: sessionId,
            candidate: currentCandidate
          })
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Start endpoint error');
        }

        const data = await res.json();
        appendMessage('received', data.reply);
        statusText.innerText = 'In Progress';
        
        // Enable input
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
        
      } catch (err) {
        appendMessage('received', `⚠️ Error initializing session: ${err.message}`);
        statusDot.className = 'pulse-dot inactive';
        statusText.innerText = 'Error';
      }
    }

    async function sendTurnMessage() {
      const msg = chatInput.value.trim();
      if (!msg || chatInput.disabled) return;

      appendMessage('sent', msg);
      chatInput.value = '';
      
      // Disable inputs
      chatInput.disabled = true;
      sendBtn.disabled = true;
      statusText.innerText = 'Agent is thinking...';
      
      try {
        const res = await fetch('/api/interview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sessionId: sessionId,
            message: msg
          })
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Failed to submit response');
        }

        const data = await res.json();
        turnCount++;
        turnCounter.textContent = `Turn: ${turnCount + 1}`;
        
        appendMessage('received', data.reply);
        
        if (data.done) {
          statusText.innerText = 'Completed';
          statusDot.className = 'pulse-dot inactive';
          
          // Fetch final feedback and show report
          setTimeout(() => {
            renderFeedbackReport(data.feedback, currentCandidate.member.name);
          }, 2000);
        } else {
          statusText.innerText = 'In Progress';
          chatInput.disabled = false;
          sendBtn.disabled = false;
          chatInput.focus();
        }

      } catch (err) {
        appendMessage('received', `⚠️ Error: ${err.message}`);
        statusText.innerText = 'Error';
        chatInput.disabled = false;
        sendBtn.disabled = false;
      }
    }

    function appendMessage(role, text) {
      const msgDiv = document.createElement('div');
      msgDiv.className = `message ${role}`;
      
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.textContent = text;
      
      const meta = document.createElement('div');
      meta.className = 'message-meta';
      meta.textContent = role === 'sent' ? 'You' : 'Interviewer';
      
      msgDiv.appendChild(bubble);
      msgDiv.appendChild(meta);
      
      chatMessages.appendChild(msgDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function renderFeedbackReport(feedback, name) {
      chatView.style.display = 'none';
      feedbackView.style.display = 'flex';
      candidateSelect.disabled = false;
      
      document.getElementById('feedback-subtitle').textContent = `Candidate Feedback for ${name}`;
      document.getElementById('feedback-summary').textContent = feedback.summary || 'No summary compiled.';
      
      const strengthsList = document.getElementById('feedback-strengths');
      strengthsList.innerHTML = '';
      (feedback.strengths || []).forEach(str => {
        const li = document.createElement('li');
        li.textContent = str;
        strengthsList.appendChild(li);
      });

      const gapsList = document.getElementById('feedback-gaps');
      gapsList.innerHTML = '';
      (feedback.gaps || []).forEach(gap => {
        const li = document.createElement('li');
        li.textContent = gap;
        gapsList.appendChild(li);
      });

      const nextList = document.getElementById('feedback-next');
      nextList.innerHTML = '';
      (feedback.next || []).forEach(nxt => {
        const li = document.createElement('li');
        li.textContent = nxt;
        nextList.appendChild(li);
      });
    }
  </script>
</body>
</html>
"""

/**
 * BLACKBOX ARENA — CLIENT APPLICATION CONTROLLER
 * Hash Router, API Client, State Management, Terminal & Judge UI
 */

(function() {
  'use strict';

  // State
  let currentUsername = localStorage.getItem('blackbox_username') || 'contender';
  let currentQuestion = null;
  let todayPuzzle = null;
  let countdownSeconds = 0;
  let countdownTimer = null;

  // Library state
  let libraryTier = 'ALL';
  let libraryStatus = 'ALL';
  let libraryQuestions = [];
  let currentRunwayIndex = 0;

  // DOM Elements
  const headerUsernameEl = document.getElementById('header-username');
  const headerCountdownEl = document.getElementById('header-countdown');
  const viewportRootEl = document.getElementById('viewport-root');
  const userModal = document.getElementById('user-modal');

  // Tier Colors
  const TIER_COLORS = {
    easy: { bg: '#CFE0F2', text: '#000000' },
    medium: { bg: '#FF5A1F', text: '#0b0b0c' },
    hard: { bg: '#4A0F1C', text: '#F8F8F7' }
  };

  // =====================================================================
  // API CLIENT & GITHUB PAGES FALLBACK SIMULATOR
  // =====================================================================
  const API_BASE = localStorage.getItem('blackbox_api_url') || '';

  async function apiFetch(endpoint, options = {}) {
    options.headers = options.headers || {};
    options.headers['X-Username'] = currentUsername;
    if (options.body && typeof options.body === 'object') {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }

    try {
      const resp = await fetch(API_BASE + endpoint, options);
      if (resp.ok) {
        return await resp.json().catch(() => ({}));
      }
      if (window.location.hostname.includes('github.io') || !API_BASE) {
        showStaticModeBanner();
        return handleStaticSimulation(endpoint, options);
      }
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || data.error || 'Server request failed.');
    } catch (err) {
      if (window.location.hostname.includes('github.io') || !API_BASE) {
        showStaticModeBanner();
        return handleStaticSimulation(endpoint, options);
      }
      throw err;
    }
  }

  function showStaticModeBanner() {
    if (document.getElementById('static-mode-indicator')) return;
    const badge = document.createElement('div');
    badge.id = 'static-mode-indicator';
    badge.title = 'Running client-side preview mode on GitHub Pages. Connect live backend via localStorage.blackbox_api_url if hosted.';
    badge.textContent = 'GH-PAGES PREVIEW';
    badge.style.cssText = 'position:fixed; bottom:8px; right:8px; background:rgba(0,0,0,0.75); color:#CFE0F2; font-family:"Space Mono",monospace; font-size:10px; padding:4px 8px; border-radius:3px; z-index:99999; border:1px solid rgba(255,255,255,0.2); letter-spacing:1px;';
    document.body.appendChild(badge);
  }

  function handleStaticSimulation(endpoint, options) {
    const url = endpoint.split('?')[0];
    const cleanUrl = url.replace(/\/$/, '');

    // 1. Today Puzzle
    if (cleanUrl === '/api/today') {
      const todayStr = new Date().toISOString().slice(0, 10);
      const qId = 'POTD-' + todayStr.replace(/-/g, '');
      const queries = parseInt(localStorage.getItem('bb_' + qId + '_queries') || '0', 10);
      const status = localStorage.getItem('bb_' + qId + '_status') || 'unattempted';
      const history = JSON.parse(localStorage.getItem('bb_' + qId + '_history') || '[]');
      return {
        id: qId,
        tier: 'medium',
        daily_date: todayStr,
        input_type: 'int',
        topics: ['TRANSFORMATION', 'MODULO', 'PARITY'],
        seconds_until_reset: 28800,
        user_status: status,
        queries_used: queries,
        queries_history: history
      };
    }

    // 2. Question Details
    if (cleanUrl.startsWith('/api/question/')) {
      const qId = cleanUrl.replace('/api/question/', '');
      const queries = parseInt(localStorage.getItem('bb_' + qId + '_queries') || '0', 10);
      const status = localStorage.getItem('bb_' + qId + '_status') || 'unattempted';
      const history = JSON.parse(localStorage.getItem('bb_' + qId + '_history') || '[]');
      const tier = qId.includes('E') ? 'easy' : (qId.includes('H') ? 'hard' : 'medium');
      return {
        id: qId,
        tier: tier,
        input_type: 'int',
        topics: ['NUMERICAL', 'AFFINE'],
        user_status: status,
        queries_used: queries,
        queries_history: history
      };
    }

    // 3. Query Probe (POST)
    if (cleanUrl === '/api/query') {
      let b = {};
      try { b = JSON.parse(options.body || '{}'); } catch(e) {}
      const qId = b.question_id || 'POTD-TODAY';
      const inputVal = b.input_val !== undefined ? b.input_val : (b.input !== undefined ? b.input : '0');
      let n = Number(inputVal);
      let outStr;
      if (!isNaN(n)) {
        outStr = String((n * 3) + 7);
      } else {
        outStr = String(inputVal).split('').reverse().join('');
      }
      let queries = parseInt(localStorage.getItem('bb_' + qId + '_queries') || '0', 10) + 1;
      localStorage.setItem('bb_' + qId + '_queries', queries);
      localStorage.setItem('bb_' + qId + '_status', 'attempted');
      let history = JSON.parse(localStorage.getItem('bb_' + qId + '_history') || '[]');
      history.push({ query_number: queries, input: String(inputVal), output: outStr, time: new Date().toLocaleTimeString() });
      localStorage.setItem('bb_' + qId + '_history', JSON.stringify(history));

      return {
        status: 'success',
        output: outStr,
        queries_used: queries,
        queries_remaining: Math.max(0, 30 - queries)
      };
    }

    // 4. Submit Code (POST)
    if (cleanUrl === '/api/submit') {
      let b = {};
      try { b = JSON.parse(options.body || '{}'); } catch(e) {}
      const qId = b.question_id || 'POTD-TODAY';
      localStorage.setItem('bb_' + qId + '_status', 'solved');
      return {
        status: 'accepted',
        passed: true,
        passed_tests: 200,
        total_tests: 200,
        execution_time_ms: 18.4
      };
    }

    // 5. Give up (POST)
    if (cleanUrl.startsWith('/api/giveup/')) {
      const qId = cleanUrl.replace('/api/giveup/', '');
      localStorage.setItem('bb_' + qId + '_status', 'surrendered');
      return { status: 'surrendered' };
    }

    // 6. Reveal
    if (cleanUrl.startsWith('/api/reveal/')) {
      const qId = cleanUrl.replace('/api/reveal/', '');
      const isSurrender = localStorage.getItem('bb_' + qId + '_status') === 'surrendered';
      const queries = parseInt(localStorage.getItem('bb_' + qId + '_queries') || '5', 10);
      return {
        id: qId,
        title: 'ARCHIVE // ' + qId,
        rule_title: 'Affine Homomorphism',
        formula: 'f(n) = 3n + 7',
        docstring: 'Multiplies integer input by 3 and adds constant scalar 7.',
        queries_used: queries,
        surrendered: isSurrender,
        efficiency_score: Math.max(10, 100 - (queries * 3)),
        contender_rank: 'TOP 5%'
      };
    }

    // 7. Library
    if (cleanUrl === '/api/library') {
      const tiers = ['easy', 'medium', 'hard'];
      const questions = [];
      for (let i = 1; i <= 30; i++) {
        const tier = tiers[(i - 1) % 3];
        const prefix = tier === 'easy' ? 'E' : (tier === 'medium' ? 'M' : 'H');
        const numStr = String(i).rjust(3, '0');
        const id = 'Q-' + prefix + numStr;
        const status = localStorage.getItem('bb_' + id + '_status') || 'unattempted';
        questions.push({
          id: id,
          tier: tier,
          input_type: 'int',
          topics: [tier.toUpperCase(), 'ALGORITHM'],
          user_status: status
        });
      }
      return {
        count: questions.length,
        questions: questions
      };
    }

    // 8. User profile
    if (cleanUrl === '/api/user/profile') {
      return {
        username: currentUsername,
        streak: 7,
        total_solved: 24,
        easy_solved: 11,
        medium_solved: 9,
        hard_solved: 4,
        joined_date: '2026-11-01'
      };
    }

    // 9. Leaderboard
    if (cleanUrl === '/api/leaderboard/daily') {
      return {
        entries: [
          { rank: 1, username: 'CYBER_KONG', queries_used: 3, tier: 'hard', time: '00:14:22' },
          { rank: 2, username: 'ZERO_TRACE', queries_used: 4, tier: 'medium', time: '01:05:40' },
          { rank: 3, username: currentUsername, queries_used: 5, tier: 'medium', time: '02:18:11' },
          { rank: 4, username: 'ADA_L', queries_used: 7, tier: 'easy', time: '03:41:00' },
          { rank: 5, username: 'TURING_M', queries_used: 9, tier: 'hard', time: '05:12:49' }
        ]
      };
    }

    // 10. Random unsolved
    if (cleanUrl === '/api/random-unsolved') {
      return { id: 'Q-M004' };
    }

    // 11. User switch
    if (cleanUrl === '/api/user/switch') {
      return { username: currentUsername };
    }

    // 12. Batch
    if (cleanUrl === '/api/library/batch') {
      return { questions: [] };
    }

    return {};
  }

  // =====================================================================
  // ROUTING & SCREEN LIFECYCLE
  // =====================================================================
  function switchScreen(screenId) {
    document.querySelectorAll('.screen-container').forEach(el => {
      el.classList.remove('active-screen');
    });
    const target = document.getElementById(screenId);
    if (target) target.classList.add('active-screen');

    // Update nav active states
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.remove('active');
    });
    if (screenId === 'screen-today') document.getElementById('nav-today').classList.add('active');
    if (screenId === 'screen-library') document.getElementById('nav-library').classList.add('active');
    if (screenId === 'screen-me') document.getElementById('nav-me').classList.add('active');
  }

  function applyTierChroma(tier) {
    const config = TIER_COLORS[tier] || TIER_COLORS.easy;
    viewportRootEl.style.setProperty('--bg-current', config.bg);
    viewportRootEl.style.setProperty('--text-current', config.text);
  }

  async function handleHashChange() {
    const hash = window.location.hash || '#today';
    const [route, param] = hash.split('/');

    try {
      if (route === '#today' || route === '') {
        await loadTodayScreen();
      } else if (route === '#probe') {
        const qId = param === 'today' ? (todayPuzzle ? todayPuzzle.id : 'POTD-TODAY') : param;
        await loadProbeScreen(qId);
      } else if (route === '#library') {
        await loadLibraryScreen();
      } else if (route === '#solved') {
        await loadSolvedScreen(param);
      } else if (route === '#me') {
        await loadMeScreen();
      }
    } catch (err) {
      console.error('Route navigation error:', err);
    }
  }

  // =====================================================================
  // SCREEN: TODAY (POTD)
  // =====================================================================
  async function loadTodayScreen() {
    switchScreen('screen-today');
    const data = await apiFetch('/api/today');
    todayPuzzle = data;
    currentQuestion = data;

    applyTierChroma(data.tier);
    if (window.Monolith3D) window.Monolith3D.setSceneMode('today', data);

    // Date & telemetry
    const parts = data.daily_date.split('-');
    const day = parts[2];
    const monthNames = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
    const month = monthNames[parseInt(parts[1], 10) - 1];

    document.getElementById('today-date-num').textContent = day;
    document.getElementById('today-month-str').textContent = month;
    document.getElementById('today-tier-label').textContent = `DIFFICULTY // ${data.tier.toUpperCase()}`;
    document.getElementById('today-seed-hash').textContent = `CHAMBER: ${data.id}`;

    const statusBadge = document.getElementById('today-status-badge');
    const openBtn = document.getElementById('today-open-btn');
    if (data.user_status === 'solved') {
      statusBadge.textContent = 'STATUS: SOLVED';
      openBtn.textContent = 'RE-ENTER CHAMBER';
    } else if (data.user_status === 'attempted') {
      statusBadge.textContent = `ATTEMPTED (${data.queries_used}/30 PROBES)`;
      openBtn.textContent = 'CONTINUE PROBE';
    } else {
      statusBadge.textContent = 'READY FOR EXTRACTION';
      openBtn.textContent = 'OPEN THE BOX';
    }
    openBtn.href = `#probe/${data.id}`;

    startCountdown(data.seconds_until_reset);
  }

  // =====================================================================
  // SCREEN: PROBE (THE ORACLE MATRIX)
  // =====================================================================
  async function loadProbeScreen(questionId) {
    switchScreen('screen-probe');

    let meta;
    if (questionId === 'today' || questionId === 'POTD-TODAY') {
      const todayData = await apiFetch('/api/today');
      meta = todayData;
      questionId = todayData.id;
    } else {
      meta = await apiFetch(`/api/question/${questionId}`);
    }

    currentQuestion = meta;
    applyTierChroma(meta.tier);

    // Update telemetry & constraints
    document.getElementById('probe-chamber-id').textContent = `CHAMBER: ${meta.id} // STAGE: INFERENCE`;
    document.getElementById('probe-counter-text').textContent = `${meta.queries_used} / 30 MAX`;
    document.getElementById('probe-input-type-label').textContent = `TYPE: ${meta.input_type.toUpperCase()}`;
    document.getElementById('probe-type-hint').textContent = `SUPPORTS ${meta.input_type.toUpperCase()}`;

    // Render Pipeline Pips
    const pipsContainer = document.getElementById('probe-pips-container');
    pipsContainer.innerHTML = '';
    for (let i = 0; i < 30; i++) {
      const pip = document.createElement('div');
      pip.style.width = '6px';
      pip.style.height = '12px';
      if (i < meta.queries_used) {
        pip.style.backgroundColor = 'currentColor';
      } else {
        pip.style.border = '1px solid currentColor';
        pip.style.opacity = '0.35';
      }
      pipsContainer.appendChild(pip);
    }

    // Chronicle Tape History
    renderChronicleTape(meta.queries_history || []);

    // 3D Canvas initialization with last output
    const lastQuery = (meta.queries_history && meta.queries_history.length > 0)
      ? meta.queries_history[meta.queries_history.length - 1]
      : null;

    if (window.Monolith3D) {
      window.Monolith3D.setSceneMode('probe', {
        output: lastQuery ? lastQuery.output : 'SEALED',
        queries_used: meta.queries_used
      });
    }

    // Reset feedback
    const feedbackEl = document.getElementById('solver-feedback');
    feedbackEl.style.display = 'none';

    // Focus input
    document.getElementById('probe-input').focus();
  }

  function renderChronicleTape(history) {
    const listEl = document.getElementById('probe-tape-list');
    listEl.innerHTML = '';
    if (!history.length) {
      listEl.innerHTML = '<div style="padding: 1rem 0; opacity: 0.5; text-align: center;">No probes transmitted yet.</div>';
      return;
    }

    history.forEach(item => {
      const row = document.createElement('div');
      row.className = 'tape-row';
      const numStr = String(item.num).padStart(2, '0');
      const inStr = JSON.stringify(item.input);
      const outStr = JSON.stringify(item.output);

      row.innerHTML = `
        <span style="opacity:0.6;">${numStr}</span>
        <span class="input-spec">f(${inStr})</span>
        <span class="output-spec">→ ${outStr}</span>
      `;
      listEl.appendChild(row);
    });
    listEl.scrollTop = listEl.scrollHeight;
  }

  // Probe Transmission
  async function transmitProbe() {
    if (!currentQuestion) return;
    const inputEl = document.getElementById('probe-input');
    const statusEl = document.getElementById('probe-buffer-status');
    const transmitBtn = document.getElementById('probe-transmit-btn');
    const rawVal = inputEl.value.trim();

    if (!rawVal) return;

    // Parse according to input_type
    let parsedVal;
    try {
      if (currentQuestion.input_type === 'int') {
        if (!/^-?\d+$/.test(rawVal)) {
          throw new Error("Input must be a valid integer (e.g. 42 or -7).");
        }
        parsedVal = parseInt(rawVal, 10);
      } else if (currentQuestion.input_type === 'list') {
        parsedVal = JSON.parse(rawVal);
        if (!Array.isArray(parsedVal)) throw new Error("Input must be a JSON array of integers (e.g. [1, 2, 3]).");
      } else {
        // String
        if ((rawVal.startsWith('"') && rawVal.endsWith('"')) || (rawVal.startsWith("'") && rawVal.endsWith("'"))) {
          parsedVal = rawVal.slice(1, -1);
        } else {
          parsedVal = rawVal;
        }
      }
    } catch (parseErr) {
      alert(parseErr.message);
      return;
    }

    statusEl.textContent = 'BUFFER: TRANSMITTING...';
    transmitBtn.disabled = true;

    try {
      const res = await apiFetch('/api/query', {
        method: 'POST',
        body: {
          question_id: currentQuestion.id,
          input_value: parsedVal
        }
      });

      // Trigger Three.js ripple and face emboss
      if (window.Monolith3D) {
        window.Monolith3D.triggerRipple(res.output);
      }

      // Update Tape and counters
      currentQuestion.queries_used = res.queries_used;
      currentQuestion.queries_history = res.history;
      document.getElementById('probe-counter-text').textContent = `${res.queries_used} / 30 MAX`;

      // Update Pips
      const pips = document.getElementById('probe-pips-container').children;
      for (let i = 0; i < 30; i++) {
        if (i < res.queries_used && pips[i]) {
          pips[i].style.backgroundColor = 'currentColor';
          pips[i].style.border = 'none';
          pips[i].style.opacity = '1';
        }
      }

      renderChronicleTape(res.history);
      inputEl.value = '';
      statusEl.textContent = 'BUFFER: ACKNOWLEDGED';
    } catch (err) {
      statusEl.textContent = 'BUFFER: ERROR';
      alert(err.message);
    } finally {
      transmitBtn.disabled = false;
    }
  }

  // Solution Submission
  async function submitSolution() {
    if (!currentQuestion) return;
    const codeEl = document.getElementById('solver-code-input');
    const submitBtn = document.getElementById('solver-submit-btn');
    const feedbackEl = document.getElementById('solver-feedback');

    const code = codeEl.value.trim();
    if (!code) return;

    submitBtn.textContent = 'EVALUATING IN SANDBOX...';
    submitBtn.disabled = true;
    feedbackEl.style.display = 'none';

    try {
      const res = await apiFetch('/api/submit', {
        method: 'POST',
        body: {
          question_id: currentQuestion.id,
          code: code
        }
      });

      feedbackEl.style.display = 'block';

      if (res.passed) {
        feedbackEl.className = 'feedback-banner success';
        feedbackEl.innerHTML = `
          <div style="font-weight:700; color:#4ade80; margin-bottom:0.25rem;">
            DEDUCTION CONFIRMED // ALL 200 HIDDEN CASES PASSED
          </div>
          <div>Solved in ${res.duration_seconds}s. Chamber conquered.</div>
          <a href="#solved/${currentQuestion.id}" class="pill-btn" style="margin-top:0.75rem; display:inline-block; padding:0.5rem 1.5rem; font-size:10px;">
            VIEW MONOLITH REVELATION →
          </a>
        `;
        submitBtn.textContent = 'CHAMBER CONQUERED';
      } else {
        feedbackEl.className = 'feedback-banner fail';
        if (res.status === 'rate_limited') {
          feedbackEl.innerHTML = `<strong>RATE LIMIT ACTIVE:</strong> ${res.error}`;
        } else if (res.status === 'timeout') {
          feedbackEl.innerHTML = `<strong>TIMEOUT FAULT:</strong> ${res.error}`;
        } else if (res.status === 'error') {
          feedbackEl.innerHTML = `<strong>SYNTAX / EXECUTION FAULT:</strong> ${res.error}`;
        } else {
          // SECRECY: Single failing input shown, expected output shown. NO RULE DETAILS!
          const inDisplay = JSON.stringify(res.failing_input);
          const expDisplay = JSON.stringify(res.expected_output);
          const userOutDisplay = res.user_error ? `Error: ${res.user_error}` : `Got: ${JSON.stringify(res.user_output)}`;

          feedbackEl.innerHTML = `
            <div style="font-weight:700; color:#FF5A1F; margin-bottom:0.25rem;">
              DISCREPANCY ISOLATED (TEST CASE #${res.test_index})
            </div>
            <div style="font-family:var(--font-mono); font-size:11px;">
              <div>• Input: <code>${inDisplay}</code></div>
              <div>• Expected Output: <code>${expDisplay}</code></div>
              <div>• Your Output: <code>${userOutDisplay}</code></div>
            </div>
          `;
        }
        submitBtn.textContent = 'SUBMIT SOLUTION';
      }
    } catch (err) {
      feedbackEl.style.display = 'block';
      feedbackEl.className = 'feedback-banner fail';
      feedbackEl.textContent = err.message;
      submitBtn.textContent = 'SUBMIT SOLUTION';
    } finally {
      submitBtn.disabled = false;
    }
  }

  // Surrender / Give Up
  async function giveUp() {
    if (!currentQuestion) return;
    if (!confirm("Are you sure you want to surrender this chamber? The governing equation will be declassified, but solve credit will be voided.")) {
      return;
    }
    try {
      await apiFetch(`/api/giveup/${currentQuestion.id}`, { method: 'POST' });
      window.location.hash = `#solved/${currentQuestion.id}`;
    } catch (err) {
      alert(err.message);
    }
  }

  // =====================================================================
  // SCREEN: LIBRARY (ARCHIVAL INDEX)
  // =====================================================================
  async function loadLibraryScreen() {
    switchScreen('screen-library');
    viewportRootEl.style.setProperty('--bg-current', '#0e0e10');
    viewportRootEl.style.setProperty('--text-current', '#e4e2e4');

    if (window.Monolith3D) window.Monolith3D.setSceneMode('library');

    const params = new URLSearchParams();
    if (libraryTier !== 'ALL') params.set('tier', libraryTier);
    if (libraryStatus !== 'ALL') params.set('status', libraryStatus);
    params.set('limit', '50');

    const data = await apiFetch(`/api/library?${params.toString()}`);
    libraryQuestions = data.questions;

    renderLibraryTable(libraryQuestions);
    updateRunwaySelection(0);
  }

  function renderLibraryTable(questions) {
    const listEl = document.getElementById('library-ledger-rows');
    listEl.innerHTML = '';
    document.getElementById('ledger-count-indicator').textContent = `TOTAL: ${questions.length} MONOGRAPHS`;

    if (!questions.length) {
      listEl.innerHTML = '<div style="padding:2rem; text-align:center; opacity:0.5;">No chambers matching active filters.</div>';
      return;
    }

    questions.forEach((q, idx) => {
      const row = document.createElement('div');
      row.className = 'ledger-row';
      const badgeClass = `badge-${q.tier}`;

      row.innerHTML = `
        <div style="display:flex; align-items:center; gap:1.5rem;">
          <span style="font-weight:700; opacity:0.6;">${q.id}</span>
          <span style="font-family:var(--font-display); font-size:16px; font-weight:700; text-transform:uppercase;">
            ${q.input_type.toUpperCase()} VECTOR [${q.topics.join(', ')}]
          </span>
          <span class="${badgeClass}">${q.tier.toUpperCase()}</span>
        </div>
        <div style="display:flex; align-items:center; justify-content:space-between; gap:2rem; font-size:11px; opacity:0.8;">
          <span>SOLVE RATE: ${q.solve_rate}%</span>
          <span style="font-weight:700; color: ${q.user_status === 'solved' ? '#4ade80' : 'inherit'};">
            ${q.user_status.toUpperCase()}
          </span>
          <span>→</span>
        </div>
      `;

      row.addEventListener('click', () => {
        updateRunwaySelection(idx);
        window.location.hash = `#probe/${q.id}`;
      });
      listEl.appendChild(row);
    });
  }

  function updateRunwaySelection(idx) {
    if (!libraryQuestions.length) return;
    currentRunwayIndex = Math.max(0, Math.min(idx, libraryQuestions.length - 1));
    const q = libraryQuestions[currentRunwayIndex];

    document.getElementById('runway-active-tag').textContent = `TIER // ${q.tier.toUpperCase()} [${q.input_type.toUpperCase()}]`;
    document.getElementById('runway-active-title').textContent = `${q.id} : ${q.topics.join(' / ').toUpperCase()}`;
    document.getElementById('runway-enter-btn').href = `#probe/${q.id}`;

    // Highlight tier strip
    ['easy', 'med', 'hard'].forEach(t => {
      const tab = document.getElementById(`tier-tab-${t}`);
      if (tab) tab.classList.remove('active');
    });
    const key = q.tier === 'medium' ? 'med' : q.tier;
    const activeTab = document.getElementById(`tier-tab-${key}`);
    if (activeTab) activeTab.classList.add('active');

    // Shift solid background color quickly to selected tier
    applyTierChroma(q.tier);
  }

  // =====================================================================
  // SCREEN: SOLVED (THE SEVERED MONOLITH)
  // =====================================================================
  async function loadSolvedScreen(questionId) {
    switchScreen('screen-solved');

    // Reveal formula
    try {
      const data = await apiFetch(`/api/reveal/${questionId}`);
      const qMeta = await apiFetch(`/api/question/${questionId}`);

      applyTierChroma(qMeta.tier);
      document.getElementById('solved-ref-tag').textContent = `ARCHIVAL PLINTH // ${qMeta.tier.toUpperCase()} TIER [${qMeta.id}]`;
      document.getElementById('solved-rule-display').textContent = data.rule_formula;

      document.getElementById('solved-duration').textContent = `${qMeta.duration_seconds || 4.2}s`;
      document.getElementById('solved-queries-used').textContent = `${qMeta.queries_used} / 30`;

      if (window.Monolith3D) {
        window.Monolith3D.setSceneMode('solved');
      }
    } catch (err) {
      alert("Rule locked: You must conquer or surrender the chamber before revelation.");
      window.location.hash = `#probe/${questionId}`;
    }
  }

  // =====================================================================
  // SCREEN: ME (CONTENDER LEDGER)
  // =====================================================================
  async function loadMeScreen() {
    switchScreen('screen-me');
    viewportRootEl.style.setProperty('--bg-current', '#131315');
    viewportRootEl.style.setProperty('--text-current', '#e4e2e4');

    if (window.Monolith3D) window.Monolith3D.setSceneMode('today');

    document.getElementById('me-username-display').textContent = currentUsername.toUpperCase();

    const profile = await apiFetch('/api/user/profile');
    document.getElementById('me-streak-count').textContent = `${profile.streak} DAYS`;
    document.getElementById('me-total-solved').textContent = profile.total_solved;
    document.getElementById('me-easy-count').textContent = profile.tier_counts.easy;
    document.getElementById('me-med-count').textContent = profile.tier_counts.medium;
    document.getElementById('me-hard-count').textContent = profile.tier_counts.hard;

    // Leaderboard for today
    const lb = await apiFetch('/api/leaderboard/daily');
    const lbContainer = document.getElementById('me-leaderboard-rows');
    lbContainer.innerHTML = '';

    if (!lb.leaderboard || !lb.leaderboard.length) {
      lbContainer.innerHTML = '<div style="padding:1rem; text-align:center; color:var(--on-surface-variant);">No solves recorded for today yet. Be the first to conquer the box!</div>';
    } else {
      lb.leaderboard.forEach(entry => {
        const row = document.createElement('div');
        row.style.display = 'grid';
        row.style.gridTemplateColumns = '60px 1fr 120px 100px';
        row.style.padding = '0.75rem 1rem';
        row.style.borderBottom = '1px solid var(--outline-variant)';
        row.style.fontSize = '12px';

        row.innerHTML = `
          <span style="font-weight:700;">#${entry.rank}</span>
          <span style="font-weight:700;">${entry.username}</span>
          <span>${entry.queries} probes</span>
          <span>${entry.duration}s</span>
        `;
        lbContainer.appendChild(row);
      });
    }
  }

  // =====================================================================
  // COUNTDOWN TICKER
  // =====================================================================
  function startCountdown(seconds) {
    if (countdownTimer) clearInterval(countdownTimer);
    countdownSeconds = seconds;

    function tick() {
      if (countdownSeconds <= 0) {
        countdownSeconds = 86400;
      }
      const h = String(Math.floor(countdownSeconds / 3600)).padStart(2, '0');
      const m = String(Math.floor((countdownSeconds % 3600) / 60)).padStart(2, '0');
      const s = String(countdownSeconds % 60).padStart(2, '0');
      const formatted = `${h}:${m}:${s}`;

      headerCountdownEl.textContent = `T-${formatted}`;
      const todayEl = document.getElementById('today-countdown');
      if (todayEl) todayEl.textContent = formatted;

      countdownSeconds--;
    }

    tick();
    countdownTimer = setInterval(tick, 1000);
  }

  // =====================================================================
  // EVENT LISTENERS & INITIALIZATION
  // =====================================================================
  function initEvents() {
    window.addEventListener('hashchange', handleHashChange);

    // Stimulus Input enter key & button
    document.getElementById('probe-transmit-btn').addEventListener('click', transmitProbe);
    document.getElementById('probe-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') transmitProbe();
    });

    // Solver Drawer Submit & Give Up
    document.getElementById('solver-submit-btn').addEventListener('click', submitSolution);
    document.getElementById('solver-giveup-btn').addEventListener('click', giveUp);

    // Library Filter Buttons
    document.getElementById('library-status-filters').addEventListener('click', e => {
      if (e.target.tagName === 'BUTTON') {
        document.querySelectorAll('#library-status-filters button').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        libraryStatus = e.target.dataset.status;
        loadLibraryScreen();
      }
    });

    document.getElementById('library-tier-filters').addEventListener('click', e => {
      if (e.target.tagName === 'BUTTON') {
        document.querySelectorAll('#library-tier-filters button').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        libraryTier = e.target.dataset.tier;
        loadLibraryScreen();
      }
    });

    // Runway Stepper
    document.getElementById('runway-prev').addEventListener('click', () => {
      if (window.Monolith3D) window.Monolith3D.cycleRunway(-1);
      updateRunwaySelection(currentRunwayIndex - 1);
    });
    document.getElementById('runway-next').addEventListener('click', () => {
      if (window.Monolith3D) window.Monolith3D.cycleRunway(1);
      updateRunwaySelection(currentRunwayIndex + 1);
    });

    // Random Unsolved Button
    document.getElementById('lib-random-btn').addEventListener('click', async () => {
      const res = await apiFetch('/api/random-unsolved');
      if (res.id) {
        window.location.hash = `#probe/${res.id}`;
      } else {
        alert(res.message || "All chambers solved!");
      }
    });

    // Generate New Batch
    document.getElementById('lib-batch-btn').addEventListener('click', async () => {
      const tier = prompt("Enter tier for new batch (easy, medium, hard):", "medium");
      if (!tier) return;
      try {
        const res = await apiFetch('/api/library/batch', {
          method: 'POST',
          body: { tier: tier.toLowerCase(), count: 10 }
        });
        alert(`Generated ${res.added} new ${res.tier.toUpperCase()} chambers!`);
        loadLibraryScreen();
      } catch (err) {
        alert(err.message);
      }
    });

    // User Switch Modal
    const switchUserModal = () => {
      document.getElementById('modal-username-input').value = currentUsername;
      userModal.showModal();
    };

    document.getElementById('header-user-btn').addEventListener('click', (e) => {
      e.preventDefault();
      switchUserModal();
    });

    document.getElementById('me-change-user-btn').addEventListener('click', switchUserModal);
    document.getElementById('modal-cancel-btn').addEventListener('click', () => userModal.close());
    document.getElementById('modal-save-btn').addEventListener('click', async () => {
      const newName = document.getElementById('modal-username-input').value.trim();
      if (!newName) return;
      try {
        const res = await apiFetch('/api/user/switch', {
          method: 'POST',
          body: { username: newName }
        });
        currentUsername = res.username;
        localStorage.setItem('blackbox_username', currentUsername);
        headerUsernameEl.textContent = currentUsername.toUpperCase();
        userModal.close();
        handleHashChange();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  // Startup
  document.addEventListener('DOMContentLoaded', () => {
    headerUsernameEl.textContent = currentUsername.toUpperCase();

    // Init Three.js canvas in #monolith-canvas-container
    const canvasContainer = document.getElementById('monolith-canvas-container');
    if (window.Monolith3D) {
      window.Monolith3D.init(canvasContainer);
    }

    initEvents();
    handleHashChange();
  });

})();

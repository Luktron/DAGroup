/**
 * ASSASSINO DA PISCADA — Main Game Client
 * Real-time multiplayer game via WebSocket.
 */

let ws;
let ROOM_CODE, PLAYER_ID, LANG, T, CFG;
let gameState = null;
let selectedTarget = null;
let chatOpen = false;
let unreadChat = 0;
let cooldowns = { kill: 0, investigate: 0 };
let cooldownTimers = {};
let chatHistory = [];  // In-memory chat history

// ─── Chat Persistence ───────────────────────────────────────────
function getChatStorageKey() {
    return `chat_history_${ROOM_CODE}`;
}

function saveChatHistory() {
    try {
        sessionStorage.setItem(getChatStorageKey(), JSON.stringify(chatHistory));
    } catch (_) { /* quota exceeded — ignore */ }
}

function loadChatHistory() {
    try {
        const saved = sessionStorage.getItem(getChatStorageKey());
        if (saved) {
            chatHistory = JSON.parse(saved);
            const container = document.getElementById('chatMessages');
            container.innerHTML = '';
            chatHistory.forEach(msg => appendChatBubble(msg, false));
            container.scrollTop = container.scrollHeight;
        }
    } catch (_) { /* corrupt data — ignore */ }
}

function appendChatBubble(msg, save) {
    const container = document.getElementById('chatMessages');
    const msgEl = document.createElement('div');
    msgEl.className = 'chat-msg';
    const iconHtml = msg.icon
        ? `<img src="${escapeHtml(msg.icon)}" class="chat-msg-icon" alt="">`
        : '';
    msgEl.innerHTML = `
        ${iconHtml}
        <span class="chat-msg-name" style="color: ${escapeHtml(msg.color)}">${escapeHtml(msg.name)}:</span>
        <span class="chat-msg-text">${escapeHtml(msg.text)}</span>`;
    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
    if (save) {
        chatHistory.push(msg);
        saveChatHistory();
    }
}

// ─── Init ────────────────────────────────────────────────────────
function initGame(opts) {
    ROOM_CODE = opts.roomCode;
    PLAYER_ID = opts.playerId;
    LANG = opts.lang;
    T = opts.translations;
    CFG = opts.config;

    loadChatHistory();
    showLoading();
    connectWebSocket();
    setupKeyboard();
    startCooldownTicker();
}

// ─── WebSocket ───────────────────────────────────────────────────
let _pingInterval = null;

function connectWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/${ROOM_CODE}/${PLAYER_ID}`);

    ws.onopen = () => {
        // Clear previous ping interval if any
        if (_pingInterval) clearInterval(_pingInterval);
        // Keep-alive ping
        _pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 25000);
    };

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        handleMessage(data);
    };

    ws.onerror = () => {
        // Connection error — will trigger onclose
    };

    ws.onclose = (e) => {
        if (_pingInterval) { clearInterval(_pingInterval); _pingInterval = null; }
        if (e.code === 4001) {
            // Player not found in room — redirect to homepage
            window.location.href = '/';
            return;
        }
        // Normal disconnect — try reconnecting
        showLoading();
        setTimeout(connectWebSocket, 2000);
    };
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

// ─── Message Router ──────────────────────────────────────────────
function handleMessage(data) {
    switch (data.type) {
        case 'state_update':
            gameState = data.state;
            renderGame();
            break;
        case 'kill_result':
            handleKillResult(data.result);
            break;
        case 'investigate_result':
            handleInvestigateResult(data.result);
            break;
        case 'accusation':
            handleAccusation(data);
            break;
        case 'look_event':
            handleLookEvent(data);
            break;
        case 'chat_message':
            handleChatMessage(data);
            break;
        case 'game_restarted':
            selectedTarget = null;
            // Clear chat for new round
            chatHistory = [];
            saveChatHistory();
            document.getElementById('chatMessages').innerHTML = '';
            break;
        case 'victim_report_broadcast':
            handleVictimReport(data);
            break;
        case 'victim_hint':
            handleVictimHintReceived(data);
            break;
        case 'hint_sent':
            // Confirmation already shown via showFeedback in submitHint
            break;
        case 'accuse_error':
            showFeedback(data.result.error, 'error');
            break;
        case 'ai_action':
            // AI action notifications for event log
            if (data.action === 'look') {
                addEventLog(`👁️ ${getPlayerName(data.actor_id)} → ${getPlayerName(data.target_id)}`, 'look');
            }
            break;
        case 'player_replaced':
            addEventLog(`🤖 ${T.ai_player} entrou no lugar`, 'noise');
            break;
        case 'pong':
            break;
    }
}

// ─── Render ──────────────────────────────────────────────────────
function renderGame() {
    if (!gameState) return;
    hideLoading();
    const me = gameState.me;

    // Always render players and header so they stay visible
    renderHeader(me);
    renderPlayerCircle(me);
    renderActionBar(me);
    updateTension(gameState.tension);
    updateBlackout(gameState.is_blackout);
    renderRecentEvents(gameState.recent_events);

    // Phase check — show game over overlay on top
    if (gameState.phase === 'finished') {
        renderGameOver();
    }
}

function renderHeader(me) {
    const roleEl = document.getElementById('roleReveal');
    const roleClass = `role-${me.role}`;
    const roleName = T[me.role] || me.role;
    const roleIconSrc = getRoleIcon(me.role, me.gender);
    roleEl.className = `role-reveal ${roleClass}`;
    roleEl.innerHTML = `<img src="${roleIconSrc}" class="role-header-icon" alt=""> ${T.you_are}: ${roleName}`;

    document.getElementById('roundBadge').textContent = `${T.round} ${gameState.round}`;
    document.getElementById('aliveBadge').textContent = `${gameState.alive_count}/${gameState.player_count} ${T.alive}`;

    // Tension meter
    document.getElementById('tensionFill').style.width = `${gameState.tension * 100}%`;
}

function renderPlayerCircle(me) {
    const circle = document.getElementById('playerCircle');
    let html = '';

    gameState.players.forEach(p => {
        const isMe = p.id === PLAYER_ID;
        const isDead = p.status === 'dead';
        const isSelected = selectedTarget === p.id;
        const suspicion = p.suspicion_score || 0;

        // Suspicion class (detective sees this)
        let suspectClass = '';
        if (me.role === 'detective' && me.has_power && !isMe && !isDead) {
            if (suspicion >= 0.7) suspectClass = 'suspect-high';
            else if (suspicion >= 0.4) suspectClass = 'suspect-moderate';
        }

        const classes = [
            'player-node',
            isDead ? 'dead' : '',
            isMe ? 'is-me' : '',
            isSelected ? 'selected' : '',
            suspectClass,
        ].filter(Boolean).join(' ');

        const aiTag = p.is_ai ? ' 🤖' : '';
        const statusIcon = isDead ? '<span class="node-status-icon">💀</span>' : '';

        // Use role icon for self, gender icon for others
        const iconSrc = p.icon || getGenderIcon(p.gender);

        // Suspicion bar (detective only)
        let suspicionBar = '';
        if (me.role === 'detective' && me.has_power && !isMe && !isDead) {
            const color = suspicion >= 0.7 ? 'var(--accent-red)'
                        : suspicion >= 0.4 ? 'var(--accent-orange)'
                        : 'var(--accent-green)';
            suspicionBar = `
                <div class="node-suspicion">
                    <div class="node-suspicion-fill" style="width: ${suspicion*100}%; background: ${color}"></div>
                </div>`;
        }

        const onclick = (!isDead && !isMe) ? `onclick="selectTarget('${p.id}')"` : '';

        html += `
            <div class="${classes}" ${onclick} data-pid="${p.id}">
                <div class="node-avatar ${isDead ? 'dead-avatar' : ''}" style="background: ${p.avatar_color}">
                    <img src="${escapeHtml(iconSrc)}" alt="" class="avatar-icon">
                    ${statusIcon}
                </div>
                <span class="node-name">${escapeHtml(p.name)}${aiTag}</span>
                ${suspicionBar}
            </div>`;
    });

    circle.innerHTML = html;
}

function getGenderIcon(gender) {
    return gender === 'f'
        ? '/images/JogadorFeminina.png'
        : '/images/JogadorMasculina.png';
}

function getRoleIcon(role, gender) {
    if (role === 'assassin') return '/images/Assassino.png';
    if (role === 'detective') return '/images/Detetive.png';
    return getGenderIcon(gender);
}

function renderActionBar(me) {
    const bar = document.getElementById('actionBar');
    if (me.status === 'dead') {
        bar.innerHTML = `<span style="color: var(--text-muted)">💀 ${T.spectator}</span>`;
        return;
    }

    let html = '';
    const hasTarget = selectedTarget !== null;

    if (me.role === 'assassin') {
        const killCD = cooldowns.kill > 0;
        html += `
            <button class="action-btn action-kill" onclick="doKill()" ${!hasTarget || killCD ? 'disabled' : ''}>
                🔪 ${T.kill}
                ${killCD ? `<span class="cooldown-indicator">${cooldowns.kill}</span>` : ''}
            </button>`;
    }

    if (me.role === 'detective' && me.has_power) {
        const invCD = cooldowns.investigate > 0;
        html += `
            <button class="action-btn action-investigate" onclick="doInvestigate()" ${!hasTarget || invCD ? 'disabled' : ''}>
                🔍 ${T.investigate}
                ${invCD ? `<span class="cooldown-indicator">${cooldowns.investigate}</span>` : ''}
            </button>
            <button class="action-btn action-accuse" onclick="doAccuse()" ${!hasTarget ? 'disabled' : ''}>
                ⚖️ ${T.accuse}
            </button>`;
    } else if (me.role === 'detective' && !me.has_power) {
        html += `<span style="color: var(--accent-red)">❌ ${T.power_lost}</span>`;
    }

    // Victim-specific: report suspicious behavior + send hint to detective
    if (me.role === 'victim') {
        html += `
            <button class="action-btn action-report" onclick="openReportModal()" ${!hasTarget ? 'disabled' : ''}>
                🚨 ${LANG === 'pt' ? 'Reportar' : 'Report'}
            </button>
            <button class="action-btn action-hint" onclick="openHintModal()" ${!hasTarget ? 'disabled' : ''}>
                💡 ${LANG === 'pt' ? 'Dica p/ Detetive' : 'Hint to Detective'}
            </button>`;
    }

    // Everyone can look
    html += `
        <button class="action-btn action-look" onclick="doLook()" ${!hasTarget ? 'disabled' : ''}>
            👁️ ${T.look_at}
        </button>`;

    bar.innerHTML = html;
}

function renderRecentEvents(events) {
    // Light event log already managed by addEventLog
}

function renderGameOver() {
    const overlay = document.getElementById('gameOverOverlay');
    const title = document.getElementById('gameOverTitle');
    const msg = document.getElementById('gameOverMessage');
    const stats = document.getElementById('gameOverStats');

    overlay.classList.remove('hidden');

    // Find the roles (revealed at game end)
    const assassin = gameState.players.find(p => p.role === 'assassin');
    const detective = gameState.players.find(p => p.role === 'detective');
    const assassinName = assassin ? escapeHtml(assassin.name) : '?';
    const detectiveName = detective ? escapeHtml(detective.name) : '?';

    const winner = gameState.winner;
    if (winner === 'detective' || winner === 'detective_auto') {
        if (winner === 'detective_auto') {
            if (LANG === 'pt') {
                title.innerHTML = `🕵️ O Detetive venceu automaticamente!`;
                msg.innerHTML = `O Detetive <strong style="color: var(--accent-cyan)">${detectiveName}</strong> venceu, pois o Assassino tentou matá-lo.`;
            } else {
                title.innerHTML = `🕵️ The Detective wins automatically!`;
                msg.innerHTML = `Detective <strong style="color: var(--accent-cyan)">${detectiveName}</strong> won because the Assassin tried to kill them.`;
            }
        } else {
            if (LANG === 'pt') {
                title.innerHTML = `🕵️ O Detetive venceu!`;
                msg.innerHTML = `O Detetive <strong style="color: var(--accent-cyan)">${detectiveName}</strong> prendeu o Assassino: <strong style="color: var(--accent-red)">${assassinName}</strong>.`;
            } else {
                title.innerHTML = `🕵️ The Detective wins!`;
                msg.innerHTML = `Detective <strong style="color: var(--accent-cyan)">${detectiveName}</strong> arrested the Assassin: <strong style="color: var(--accent-red)">${assassinName}</strong>.`;
            }
        }
        title.style.color = 'var(--accent-cyan)';
        SoundFX.victory();
    } else {
        if (LANG === 'pt') {
            title.innerHTML = `🔪 O Assassino venceu!`;
            msg.innerHTML = `O Assassino <strong style="color: var(--accent-red)">${assassinName}</strong> matou todas as vítimas.`;
        } else {
            title.innerHTML = `🔪 The Assassin wins!`;
            msg.innerHTML = `Assassin <strong style="color: var(--accent-red)">${assassinName}</strong> eliminated all victims.`;
        }
        title.style.color = 'var(--accent-red)';
        SoundFX.gameOver();
    }

    // Show all roles with icons
    let statsHtml = '<div style="margin-top: 0.8rem; text-align: left; font-size: 0.85rem;">';
    gameState.players.forEach(p => {
        const roleName = T[p.role] || p.role || '?';
        const icon = p.icon || getGenderIcon(p.gender);
        const statusIcon = p.status === 'dead' ? ' 💀' : '';
        const roleColor = p.role === 'assassin' ? 'var(--accent-red)'
                        : p.role === 'detective' ? 'var(--accent-cyan)'
                        : 'var(--accent-green)';
        statsHtml += `<div style="display:flex; align-items:center; gap:0.4rem; margin:0.3rem 0;">
            <img src="${escapeHtml(icon)}" style="width:24px;height:24px;border-radius:50%;">
            <span>${escapeHtml(p.name)}${statusIcon}</span>
            <span style="color:${roleColor}; font-weight:600; margin-left:auto;">${roleName}</span>
        </div>`;
    });
    statsHtml += '</div>';
    stats.innerHTML = statsHtml;

    const me = gameState.me;
    const btnPlay = document.getElementById('btnPlayAgain');
    const waitingMsg = document.getElementById('waitingHostMsg');
    if (gameState.is_creator) {
        btnPlay.style.display = 'inline-flex';
        if (waitingMsg) waitingMsg.style.display = 'none';
    } else {
        btnPlay.style.display = 'none';
        if (waitingMsg) waitingMsg.style.display = 'block';
    }
}

// ─── Actions ─────────────────────────────────────────────────────
function selectTarget(pid) {
    if (selectedTarget === pid) {
        selectedTarget = null;
    } else {
        selectedTarget = pid;
    }
    renderPlayerCircle(gameState.me);
    renderActionBar(gameState.me);
    SoundFX.look();
}

function doKill() {
    if (!selectedTarget) return;
    send({ type: 'kill', target_id: selectedTarget });
    startCooldown('kill', CFG.assassinCooldown);
    SoundFX.kill();
    selectedTarget = null;
}

function doInvestigate() {
    if (!selectedTarget) return;
    send({ type: 'investigate', target_id: selectedTarget });
    startCooldown('investigate', CFG.detectiveCooldown);
    SoundFX.investigate();
}

function doAccuse() {
    if (!selectedTarget) return;
    const name = getPlayerName(selectedTarget);
    if (confirm(`${T.accuse} ${name}? ⚠️`)) {
        send({ type: 'accuse', target_id: selectedTarget });
        SoundFX.accuse();
        selectedTarget = null;
    }
}

function doLook() {
    if (!selectedTarget) return;
    send({ type: 'look', target_id: selectedTarget });
    showFeedback(`👁️ ${T.look_registered}`, 'success');
    SoundFX.look();
}

function playAgain() {
    send({ type: 'play_again' });
    document.getElementById('gameOverOverlay').classList.add('hidden');
}

function leaveGame() {
    const msg = LANG === 'pt'
        ? 'Você realmente deseja sair da partida?'
        : 'Do you really want to leave the game?';
    if (confirm(msg)) {
        send({ type: 'leave_game' });
        window.location.href = '/';
    }
}

// ─── Result Handlers ─────────────────────────────────────────────
function handleKillResult(result) {
    if (result.detective_auto_win) {
        showFeedback(LANG === 'pt'
            ? '🕵️ O Detetive venceu automaticamente!'
            : '🕵️ The Detective wins automatically!', 'error');
    } else if (result.success) {
        showFeedback(`🔪 ${LANG === 'pt' ? 'Alvo marcado...' : 'Target marked...'}`, 'kill');
    } else if (result.error === 'cooldown') {
        showFeedback(`⏳ ${T.cooldown_active} (${result.remaining}s)`, 'error');
    }
}

function handleInvestigateResult(result) {
    if (!result.success) {
        showFeedback(result.error, 'error');
        return;
    }

    const evidence = result.evidence;
    const panel = document.getElementById('investigationPanel');
    const content = document.getElementById('investigationContent');

    const levelClass = `evidence-level-${evidence.level}`;
    const levelText = evidence.level === 'high' ? T.high_suspicion
                    : evidence.level === 'moderate' ? T.moderate_suspicion
                    : evidence.level === 'low' ? T.suspicious_activity
                    : T.no_evidence;

    const name = getPlayerName(evidence.player_id);
    let hintsHtml = evidence.hints.map(h => `<li>${escapeHtml(h)}</li>`).join('');

    let timelineHtml = '';
    if (evidence.timeline_snippets && evidence.timeline_snippets.length > 0) {
        timelineHtml = `<div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-muted)">
            <strong>Timeline:</strong><br>
            ${evidence.timeline_snippets.map(s =>
                `<span>${s.type} (${s.seconds_ago}s ago)</span>`
            ).join(' | ')}
        </div>`;
    }

    content.innerHTML = `
        <div class="evidence-item">
            <strong>${escapeHtml(name)}</strong>
            <span class="${levelClass}" style="margin-left: 0.5rem; font-weight: 700">● ${levelText}</span>
            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.3rem">
                Score: ${evidence.score} | Atividades recentes: ${evidence.recent_activity_count}
            </div>
            <ul class="evidence-hints">${hintsHtml}</ul>
            ${timelineHtml}
        </div>`;

    panel.classList.remove('hidden');
    // Auto-hide after 10s
    setTimeout(() => panel.classList.add('hidden'), 10000);
}

function handleAccusation(data) {
    const detectiveName = getPlayerName(data.detective_id);
    const suspectName = getPlayerName(data.suspect_id);

    if (data.correct) {
        showFeedback(`⚖️ ${T.arrested} ${suspectName}!`, 'success');
        SoundFX.victory();
    } else {
        showFeedback(`❌ ${T.wrong_accusation}`, 'error');
        SoundFX.error();
    }

    addEventLog(`⚖️ ${detectiveName} → ${suspectName}: ${data.correct ? '✅' : '❌'}`, 'accuse');
}

function handleLookEvent(data) {
    // Show look indicator on target
    const node = document.querySelector(`[data-pid="${data.target_id}"]`);
    if (node) {
        const indicator = document.createElement('div');
        indicator.className = 'look-indicator';
        indicator.textContent = `👁️ ${data.actor_name}`;
        node.appendChild(indicator);
        setTimeout(() => indicator.remove(), 2000);
    }

    if (data.actor_id !== PLAYER_ID) {
        addEventLog(`👁️ ${data.actor_name} → ${data.target_name}`, 'look');
    }
}

function handleChatMessage(data) {
    appendChatBubble({
        name: data.player_name,
        color: data.avatar_color,
        text: data.message,
        icon: data.icon || null,
    }, true);

    if (!chatOpen) {
        unreadChat++;
        const badge = document.getElementById('chatBadge');
        badge.textContent = unreadChat;
        badge.classList.remove('hidden');
    }
    SoundFX.chat();
}

// ─── UI Helpers ──────────────────────────────────────────────────
function showLoading() {
    let el = document.getElementById('loadingOverlay');
    if (!el) {
        el = document.createElement('div');
        el.id = 'loadingOverlay';
        el.className = 'loading-overlay';
        el.innerHTML = `<div class="loading-spinner"></div><p>${LANG === 'pt' ? 'Conectando...' : 'Connecting...'}</p>`;
        document.getElementById('gameContainer').appendChild(el);
    }
    el.classList.remove('hidden');
}

function hideLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.add('hidden');
}

function showFeedback(text, type) {
    const container = document.getElementById('actionFeedback');
    const toast = document.createElement('div');
    toast.className = `feedback-toast feedback-${type}`;
    toast.textContent = text;
    container.innerHTML = '';
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function addEventLog(text, type) {
    const log = document.getElementById('eventLog');
    if (!log) return;
    const entry = document.createElement('div');
    entry.className = `event-entry event-${type}`;
    entry.textContent = text;
    log.appendChild(entry);
    // Keep only last 15
    while (log.children.length > 15) {
        log.removeChild(log.firstChild);
    }
    log.scrollTop = log.scrollHeight;
}

function handleVictimReport(data) {
    // Show report as a system message in chat so detective and others can see it
    const reportLabel = LANG === 'pt' ? 'REPORTE' : 'REPORT';
    appendChatBubble({
        name: `🚨 ${reportLabel}`,
        color: '#43E97B',
        text: `${data.reporter_name} → ${data.target_name}: "${data.reason}"`
    }, true);

    // Also log it to event log
    addEventLog(`🚨 ${data.reporter_name} → ${data.target_name}`, 'report');

    if (!chatOpen) {
        unreadChat++;
        const badge = document.getElementById('chatBadge');
        badge.textContent = unreadChat;
        badge.classList.remove('hidden');
    }
    SoundFX.chat();
}

function handleVictimHintReceived(data) {
    // This is only received by the detective — show as a private hint in chat
    const hintLabel = LANG === 'pt' ? 'DICA' : 'HINT';
    const aboutText = data.target_name
        ? (LANG === 'pt' ? ` sobre ${data.target_name}` : ` about ${data.target_name}`)
        : '';
    appendChatBubble({
        name: `💡 ${hintLabel} (${data.from_name})`,
        color: '#00C9FF',
        text: `${data.hint}${aboutText}`,
        icon: data.icon || null,
    }, true);

    // Also show as a toast so detective doesn't miss it
    showFeedback(`💡 ${data.from_name}: "${data.hint}"`, 'success');

    if (!chatOpen) {
        unreadChat++;
        const badge = document.getElementById('chatBadge');
        badge.textContent = unreadChat;
        badge.classList.remove('hidden');
    }
    SoundFX.chat();
}

function updateTension(level) {
    const overlay = document.getElementById('tensionOverlay');
    if (overlay) {
        overlay.style.setProperty('--tension-alpha', level * 0.3);
    }

    // Tension sound at high levels
    if (level > 0.7 && Math.random() < 0.05) {
        SoundFX.tension();
    }
}

function updateBlackout(isBlackout) {
    const overlay = document.getElementById('blackoutOverlay');
    if (overlay) {
        if (isBlackout) {
            overlay.classList.add('active');
            SoundFX.blackout();
        } else {
            overlay.classList.remove('active');
        }
    }
}

function toggleChat() {
    const panel = document.getElementById('chatPanel');
    chatOpen = !chatOpen;
    if (chatOpen) {
        panel.classList.remove('hidden');
        unreadChat = 0;
        document.getElementById('chatBadge').classList.add('hidden');
        const input = document.getElementById('chatInput');
        const sendBtn = panel.querySelector('.chat-input-row button');
        if (gameState && gameState.me && gameState.me.status === 'dead') {
            input.disabled = true;
            input.placeholder = LANG === 'pt' ? 'Espectadores não podem falar' : 'Spectators cannot chat';
            if (sendBtn) sendBtn.disabled = true;
        } else {
            input.disabled = false;
            input.placeholder = LANG === 'pt' ? 'Mensagem...' : 'Message...';
            if (sendBtn) sendBtn.disabled = false;
            input.focus();
        }
    } else {
        panel.classList.add('hidden');
    }
}

function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;
    send({ type: 'chat', message: msg });
    input.value = '';
}

// ─── Victim Report System ────────────────────────────────────────
function openReportModal() {
    if (!selectedTarget || !gameState) return;
    const targetName = getPlayerName(selectedTarget);

    const reportReasons = LANG === 'pt'
        ? [
            'Está agindo de forma suspeita',
            'Estava olhando muito para alguém',
            'Evita contato visual',
            'Comportamento estranho após uma morte',
            'Parece nervoso(a)'
          ]
        : [
            'Acting suspiciously',
            'Staring at someone a lot',
            'Avoiding eye contact',
            'Strange behavior after a death',
            'Seems nervous'
          ];

    const overlay = document.createElement('div');
    overlay.className = 'report-modal-overlay';
    overlay.id = 'reportModalOverlay';

    const title = LANG === 'pt'
        ? `🚨 Reportar ${escapeHtml(targetName)}`
        : `🚨 Report ${escapeHtml(targetName)}`;
    const cancelText = LANG === 'pt' ? 'Cancelar' : 'Cancel';

    let optionsHtml = reportReasons.map((reason, i) =>
        `<button class="report-option" data-reason="${escapeHtml(reason)}">${escapeHtml(reason)}</button>`
    ).join('');

    overlay.innerHTML = `
        <div class="report-modal">
            <h3>${title}</h3>
            <div class="report-options">${optionsHtml}</div>
            <button class="btn btn-ghost btn-sm" data-action="cancel">${cancelText}</button>
        </div>`;

    document.body.appendChild(overlay);

    // Delegate click events (avoids inline JS / XSS)
    overlay.addEventListener('click', (e) => {
        const reasonBtn = e.target.closest('[data-reason]');
        if (reasonBtn) { submitReport(reasonBtn.dataset.reason); return; }
        if (e.target.closest('[data-action="cancel"]')) { closeReportModal(); return; }
        if (e.target === overlay) closeReportModal();
    });

}

function closeReportModal() {
    const overlay = document.getElementById('reportModalOverlay');
    if (overlay) overlay.remove();
}

function submitReport(reason) {
    if (!selectedTarget) return;
    send({
        type: 'victim_report',
        target_id: selectedTarget,
        reason: reason
    });
    const feedbackText = LANG === 'pt' ? '🚨 Reporte enviado!' : '🚨 Report sent!';
    showFeedback(feedbackText, 'success');
    closeReportModal();
    selectedTarget = null;
    if (gameState) {
        renderPlayerCircle(gameState.me);
        renderActionBar(gameState.me);
    }
}

function getPlayerName(pid) {
    if (!gameState) return pid;
    const p = gameState.players.find(pl => pl.id === pid);
    return p ? p.name : pid;
}

// ─── Victim Hint System ──────────────────────────────────────────
function openHintModal() {
    if (!selectedTarget || !gameState) return;
    const targetName = getPlayerName(selectedTarget);

    const hints = LANG === 'pt'
        ? [
            'Acho que essa pessoa é o assassino',
            'Essa pessoa está agindo de forma estranha',
            'Essa pessoa evita contato visual',
            'Vi algo suspeito sobre essa pessoa',
            'Fique de olho nessa pessoa'
          ]
        : [
            'I think this person is the assassin',
            'This person is acting strangely',
            'This person avoids eye contact',
            'I saw something suspicious about them',
            'Keep an eye on this person'
          ];

    const overlay = document.createElement('div');
    overlay.className = 'report-modal-overlay';
    overlay.id = 'hintModalOverlay';

    const title = LANG === 'pt'
        ? `💡 Dica sobre ${escapeHtml(targetName)}`
        : `💡 Hint about ${escapeHtml(targetName)}`;
    const cancelText = LANG === 'pt' ? 'Cancelar' : 'Cancel';
    const customLabel = LANG === 'pt' ? 'Dica personalizada:' : 'Custom hint:';
    const sendText = LANG === 'pt' ? 'Enviar' : 'Send';

    let optionsHtml = hints.map(h =>
        `<button class="report-option" data-hint="${escapeHtml(h)}">${escapeHtml(h)}</button>`
    ).join('');

    overlay.innerHTML = `
        <div class="report-modal">
            <h3>${title}</h3>
            <div class="report-options">${optionsHtml}</div>
            <div style="margin-top: 0.5rem;">
                <label style="font-size: 0.8rem; color: var(--text-secondary)">${customLabel}</label>
                <div style="display:flex; gap:0.3rem; margin-top:0.3rem;">
                    <input type="text" id="customHintInput" maxlength="200" style="flex:1; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:0.4rem 0.8rem; color:var(--text-primary); font-size:0.85rem;">
                    <button class="btn btn-primary btn-sm" data-action="send-custom">${sendText}</button>
                </div>
            </div>
            <button class="btn btn-ghost btn-sm" data-action="cancel" style="margin-top:0.5rem;">${cancelText}</button>
        </div>`;

    document.body.appendChild(overlay);

    overlay.addEventListener('click', (e) => {
        const hintBtn = e.target.closest('[data-hint]');
        if (hintBtn) { submitHint(hintBtn.dataset.hint); return; }
        if (e.target.closest('[data-action="send-custom"]')) {
            const input = document.getElementById('customHintInput');
            const text = input ? input.value.trim() : '';
            if (text) submitHint(text);
            return;
        }
        if (e.target.closest('[data-action="cancel"]')) { closeHintModal(); return; }
        if (e.target === overlay) closeHintModal();
    });

    overlay.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const input = document.getElementById('customHintInput');
            const text = input ? input.value.trim() : '';
            if (text) submitHint(text);
        }
    });
}

function closeHintModal() {
    const overlay = document.getElementById('hintModalOverlay');
    if (overlay) overlay.remove();
}

function submitHint(hint) {
    if (!selectedTarget) return;
    send({
        type: 'victim_hint',
        target_id: selectedTarget,
        hint: hint
    });
    const feedbackText = LANG === 'pt' ? '💡 Dica enviada ao detetive!' : '💡 Hint sent to detective!';
    showFeedback(feedbackText, 'success');
    closeHintModal();
    selectedTarget = null;
    if (gameState) {
        renderPlayerCircle(gameState.me);
        renderActionBar(gameState.me);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Cooldown System ─────────────────────────────────────────────
function startCooldown(action, seconds) {
    cooldowns[action] = seconds;
}

function startCooldownTicker() {
    setInterval(() => {
        let changed = false;
        for (const key of Object.keys(cooldowns)) {
            if (cooldowns[key] > 0) {
                cooldowns[key]--;
                changed = true;
            }
        }
        if (changed && gameState) {
            renderActionBar(gameState.me);
        }
    }, 1000);
}

// ─── Keyboard ────────────────────────────────────────────────────
function setupKeyboard() {
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT') {
            if (e.key === 'Enter' && e.target.id === 'chatInput') {
                sendChat();
            }
            return;
        }

        if (e.key === 'k' || e.key === 'K') doKill();
        if (e.key === 'i' || e.key === 'I') doInvestigate();
        if (e.key === 'l' || e.key === 'L') doLook();
        if (e.key === 'c' || e.key === 'C') toggleChat();
        if (e.key === 'Escape') {
            selectedTarget = null;
            if (gameState) {
                renderPlayerCircle(gameState.me);
                renderActionBar(gameState.me);
            }
            document.getElementById('investigationPanel')?.classList.add('hidden');
        }
    });
}

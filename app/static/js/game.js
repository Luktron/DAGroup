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

// ─── Init ────────────────────────────────────────────────────────
function initGame(opts) {
    ROOM_CODE = opts.roomCode;
    PLAYER_ID = opts.playerId;
    LANG = opts.lang;
    T = opts.translations;
    CFG = opts.config;

    connectWebSocket();
    setupKeyboard();
    startCooldownTicker();
}

// ─── WebSocket ───────────────────────────────────────────────────
function connectWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/${ROOM_CODE}/${PLAYER_ID}`);

    ws.onopen = () => {
        // Keep-alive ping
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 25000);
    };

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        setTimeout(connectWebSocket, 3000);
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
    const me = gameState.me;

    // Phase check
    if (gameState.phase === 'finished') {
        renderGameOver();
        return;
    }

    // Header
    renderHeader(me);
    // Player circle
    renderPlayerCircle(me);
    // Action bar
    renderActionBar(me);
    // Tension overlay
    updateTension(gameState.tension);
    // Blackout
    updateBlackout(gameState.is_blackout);
    // Events
    renderRecentEvents(gameState.recent_events);
}

function renderHeader(me) {
    const roleEl = document.getElementById('roleReveal');
    const roleClass = `role-${me.role}`;
    const roleName = T[me.role] || me.role;
    const roleIcon = me.role === 'assassin' ? '🔪' : me.role === 'detective' ? '🕵️' : '😊';
    roleEl.className = `role-reveal ${roleClass}`;
    roleEl.innerHTML = `${roleIcon} ${T.you_are}: ${roleName}`;

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

        const avatarClass = isDead ? 'node-avatar dead-avatar' : 'node-avatar';
        const initial = p.name ? p.name.charAt(0).toUpperCase() : '?';
        const aiTag = p.is_ai ? ' 🤖' : '';
        const statusIcon = isDead ? '<span class="node-status-icon">💀</span>' : '';

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
                <div class="${avatarClass}" style="background: ${p.avatar_color}">
                    ${isDead ? '' : initial}
                    ${statusIcon}
                </div>
                <span class="node-name">${escapeHtml(p.name)}${aiTag}</span>
                ${suspicionBar}
            </div>`;
    });

    circle.innerHTML = html;
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

    const winner = gameState.winner;
    if (winner === 'detective') {
        title.innerHTML = `🕵️ ${T.detective_wins}`;
        title.style.color = 'var(--accent-cyan)';
        SoundFX.victory();
    } else {
        title.innerHTML = `🔪 ${T.assassin_wins}`;
        title.style.color = 'var(--accent-red)';
        SoundFX.gameOver();
    }

    // Find the roles
    const assassin = gameState.players.find(p => p.role === 'assassin');
    const detective = gameState.players.find(p => p.role === 'detective');

    msg.innerHTML = `
        ${T.assassin}: <strong style="color: var(--accent-red)">${assassin ? escapeHtml(assassin.name) : '?'}</strong><br>
        ${T.detective}: <strong style="color: var(--accent-cyan)">${detective ? escapeHtml(detective.name) : '?'}</strong>
    `;

    const me = gameState.me;
    const isCreator = gameState.players.length > 0;
    const btnPlay = document.getElementById('btnPlayAgain');
    // Show play again for all players
    btnPlay.style.display = 'inline-flex';
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

// ─── Result Handlers ─────────────────────────────────────────────
function handleKillResult(result) {
    if (result.success) {
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
    const container = document.getElementById('chatMessages');
    const msgEl = document.createElement('div');
    msgEl.className = 'chat-msg';
    msgEl.innerHTML = `
        <span class="chat-msg-name" style="color: ${data.avatar_color}">${escapeHtml(data.player_name)}:</span>
        <span class="chat-msg-text">${escapeHtml(data.message)}</span>`;
    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;

    if (!chatOpen) {
        unreadChat++;
        const badge = document.getElementById('chatBadge');
        badge.textContent = unreadChat;
        badge.classList.remove('hidden');
    }
    SoundFX.chat();
}

// ─── UI Helpers ──────────────────────────────────────────────────
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
        document.getElementById('chatInput').focus();
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

function getPlayerName(pid) {
    if (!gameState) return pid;
    const p = gameState.players.find(pl => pl.id === pid);
    return p ? p.name : pid;
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

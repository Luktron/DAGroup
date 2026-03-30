# MAUI_DAG — Especificação Completa para Migração .NET MAUI Android

## Documento de Referência para Agent LLM (Claude Opus 4.6)

**Objetivo:** Criar uma aplicação .NET MAUI Android completa baseada no jogo "Assassino da Piscada" (Blink Assassin), que funcione como aplicação nativa Android e gere APK. Este documento descreve TODA a lógica, regras, funcionalidades e arquitetura da aplicação Python/FastAPI existente para que seja fielmente recriada em .NET MAUI.

---

## 1. VISÃO GERAL DO JOGO

**Nome:** Assassino da Piscada / Blink Assassin  
**Tipo:** Jogo multiplayer social de dedução em tempo real  
**Plataforma alvo:** Android (APK via .NET MAUI)  
**Idiomas:** Português (PT) e Inglês (EN) — bilíngue com toggle  
**Jogadores:** Mínimo 3, máximo 12, ideal 6  
**Comunicação:** WebSocket em tempo real (latência < 200ms)

### Conceito
Baseado no jogo presencial onde um assassino oculto elimina vítimas "piscando" para elas, enquanto um detetive tenta identificá-lo. Na versão digital, a "piscada" é substituída por um sistema de ação secreta com delay aleatório e camuflagem por eventos falsos.

### Papéis
- **Assassino (1):** Elimina vítimas secretamente via "piscada digital"
- **Detetive (1):** Investiga jogadores, analisa padrões, acusa o assassino
- **Vítimas (restante):** Observam, reportam comportamentos suspeitos, enviam dicas ao detetive

---

## 2. CONFIGURAÇÕES DO JOGO (GameConfig)

Todos os valores são constantes imutáveis:

```
Sala:
  MIN_PLAYERS = 3
  MAX_PLAYERS = 12
  DEFAULT_PLAYERS = 6

Tempos (segundos):
  KILL_DELAY_MIN = 2          # Delay mínimo antes da morte executar
  KILL_DELAY_MAX = 8          # Delay máximo antes da morte executar
  ASSASSIN_COOLDOWN = 10      # Intervalo mínimo entre ações do assassino
  DETECTIVE_COOLDOWN = 12     # Intervalo mínimo entre investigações
  ROUND_DURATION = 120        # Duração da rodada (referência, não enforced)
  LOBBY_COUNTDOWN = 10        # Countdown para início
  NOISE_EVENT_INTERVAL = 3    # Intervalo entre eventos de ruído

Detetive - Investigação:
  INVESTIGATION_WINDOW = 15   # Segundos de logs visíveis na investigação
  SUSPICION_DECAY = 0.05      # Decaimento de suspeita por segundo
  FALSE_ACCUSATION_PENALTY = "lose_power"  # "lose_power" ou "die"
                                           # Atualmente: detetive morre e assassino vence

IA:
  AI_THINK_DELAY_MIN = 1.5    # Delay mínimo entre decisões IA
  AI_THINK_DELAY_MAX = 5.0    # Delay máximo entre decisões IA
  AI_KILL_INTERVAL_MIN = 8    # Intervalo mínimo entre kills IA
  AI_KILL_INTERVAL_MAX = 18   # Intervalo máximo entre kills IA
  AI_INVESTIGATE_INTERVAL_MIN = 10
  AI_INVESTIGATE_INTERVAL_MAX = 20
  AI_LOOK_INTERVAL_MIN = 3
  AI_LOOK_INTERVAL_MAX = 8

Eventos:
  BLACKOUT_DURATION = 8       # Duração do apagão em segundos
  BLACKOUT_CHANCE = 0.15      # 15% chance de apagão após uma morte
  INTERFERENCE_CHANCE = 0.10  # 10% chance de interferência

Balanceamento:
  DETECTIVE_WIN_RATE_TARGET = 0.35
  ASSASSIN_WIN_RATE_TARGET = 0.45

Servidor:
  HOST = "0.0.0.0"
  PORT = 5052
  SECRET_KEY = random
  DEFAULT_LANG = "pt"
```

---

## 3. SISTEMA DE PAPÉIS (Roles)

### 3.1 Enum RoleType
```
ASSASSIN = "assassin"
DETECTIVE = "detective"
VICTIM = "victim"
```

### 3.2 Enum PlayerStatus
```
ALIVE = "alive"
DEAD = "dead"
SPECTATOR = "spectator"
```

### 3.3 Modelo Player — Propriedades
```
id: string               # Identificador único (ex: "p_abc123def4")
name: string              # Nome do jogador (máx 20 chars, sanitizado)
role: RoleType?           # Papel (null no lobby)
status: PlayerStatus      # Estado atual (padrão: ALIVE)
is_ai: bool               # Se é bot IA
avatar_color: string      # Cor hex do avatar
gender: string            # "m" ou "f"

last_action_time: float   # Timestamp da última ação (para cooldown)
action_count: int          # Contador de ações totais
has_power: bool           # Detetive perde poder ao errar acusação
investigations_used: int   # Quantas investigações o detetive usou
suspicion_score: float    # Score de suspeita (0.0 a 1.0)

look_targets: list[str]   # IDs dos jogadores que este olhou
looked_at_by: list[str]   # IDs dos jogadores que olharam para este

kills: int                # Kills realizados
correct_accusations: int   # Acusações corretas
wrong_accusations: int     # Acusações erradas
```

### 3.4 Ícones de Avatar
Existem 4 imagens PNG:
- `Assassino.png` — Ícone do assassino (visível só para o próprio assassino e após fim do jogo)
- `Detetive.png` — Ícone do detetive (visível só para o próprio detetive e após fim do jogo)
- `JogadorMasculina.png` — Ícone masculino (para vítimas e ícone público de todos)
- `JogadorFeminina.png` — Ícone feminino (para vítimas e ícone público de todos)

**Regra:** Durante o jogo, todos os jogadores veem ícones de gênero para os outros. Cada jogador vê seu próprio ícone de papel. Após fim de jogo, todos os papéis são revelados com ícones reais.

### 3.5 Cores de Avatar
12 cores cíclicas:
```
"#6C63FF", "#FF6584", "#43E97B", "#F7971E",
"#00C9FF", "#FC5C7D", "#A18CD1", "#FBC2EB",
"#F093FB", "#4FACFE", "#0BA360", "#FFD54F"
```
Atribuídas na ordem de entrada do jogador na sala.

### 3.6 Serialização do Player

**Visão Pública (to_public_dict):** id, name, status, is_ai, avatar_color, gender, suspicion_score

**Visão Privada (to_private_dict):** Tudo da pública + role, has_power, investigations_used, kills, icon (ícone do papel real)

**Visão do Detetive (to_detective_view):** Tudo da pública + suspicion_score, recent_looks (últimos 5 looks), action_count

**Ícone Público (get_public_icon):** Retorna ícone baseado apenas no gênero (nunca revela o papel)

---

## 4. MOTOR DO JOGO (Engine)

### 4.1 Fases do Jogo (GamePhase)
```
LOBBY = "lobby"       # Esperando jogadores
PLAYING = "playing"   # Jogo em andamento
FINISHED = "finished" # Jogo encerrado
```

### 4.2 Sala de Jogo (GameRoom) — Propriedades
```
room_code: string        # Código de 6 caracteres hex maiúsculos (ex: "A1B2C3")
creator_id: string       # ID do criador da sala
max_players: int         # Limitado entre MIN_PLAYERS e MAX_PLAYERS
lang: string             # "pt" ou "en"
phase: GamePhase         # Fase atual
players: dict[str, Player]  # Mapa ID → Player
player_order: list[str]     # Ordem dos jogadores no círculo (shuffled)
round_number: int        # Número da rodada atual
round_start_time: float  # Timestamp do início da rodada
timeline: EventTimeline  # Histórico de eventos
suspicion: SuspicionEngine # Motor de suspeita
pending_kills: list[PendingKill]  # Kills agendados (delay)
winner: string?          # "assassin", "detective", "assassin_accuse", "detective_auto"
is_blackout: bool        # Se está em apagão
blackout_end: float      # Quando o apagão termina
created_at: float        # Timestamp de criação
```

### 4.3 Gestão de Jogadores

**Adicionar jogador (add_player):**
- Verifica se sala não está cheia
- Atribui cor de avatar cíclica
- Registra na timeline (PLAYER_JOIN) e no motor de suspeita
- Retorna Player ou None

**Remover jogador (remove_player):**
- Remove de players, player_order, suspicion
- Registra PLAYER_LEAVE na timeline

**Queries:**
- `get_alive_players()`: Todos com status ALIVE
- `get_alive_victims()`: Apenas vítimas ALIVE
- `get_player_by_role(role)`: Primeiro jogador com o papel dado

### 4.4 Ciclo de Vida do Jogo

**Atribuição de Papéis (assign_roles):**
1. Pega lista de todos os IDs
2. Shuffle aleatório
3. Primeiro → ASSASSIN
4. Segundo → DETECTIVE
5. Restante → VICTIM
6. Shuffle separado da ordem do círculo (player_order)

**Iniciar Jogo (start_game):**
- Requer mínimo MIN_PLAYERS
- Requer fase LOBBY
- Chama assign_roles()
- Muda fase para PLAYING
- Incrementa round_number para 1
- Define round_start_time
- Registra GAME_START na timeline

**Encerrar Jogo (end_game):**
- Muda fase para FINISHED
- Define winner
- Registra GAME_END na timeline

**Reset para Nova Rodada (reset_for_new_round):**
- Para CADA jogador: reseta role=None, status=ALIVE, has_power=True, last_action_time=0, action_count=0, investigations_used=0, suspicion_score=0, look_targets=[], looked_at_by=[]
- Limpa pending_kills, winner, is_blackout
- Recria timeline e suspicion engine (novos objetos)
- Registra todos no suspeita novamente
- Chama assign_roles()
- Muda para PLAYING, incrementa round_number

### 4.5 Ações do Jogo

#### 4.5.1 Kill do Assassino (assassin_kill)

**Entrada:** assassin_id, target_id

**Validações:**
1. Jogador deve ser ASSASSIN
2. Assassino deve estar ALIVE
3. Alvo deve existir e estar ALIVE
4. Alvo não pode ser o próprio ASSASSIN

**Regra especial — Se alvo for DETECTIVE:**
- Jogo termina automaticamente com vitória do detetive (`winner = "detective_auto"`)
- O assassino NÃO consegue matar o detetive

**Cooldown:**
- Verifica se `time_now - last_action_time >= ASSASSIN_COOLDOWN`
- Se em cooldown, retorna erro com remaining seconds

**Execução com Delay:**
1. Calcula delay aleatório entre KILL_DELAY_MIN e KILL_DELAY_MAX
2. Cria PendingKill com execute_at = now + delay
3. Adiciona à lista pending_kills
4. Atualiza last_action_time e action_count do assassino

**Camuflagem:**
1. Gera 2 a 4 eventos falsos (NoiseGenerator) com IDs aleatórios
2. Eventos de ruído incluem "olhar suspeito", "movimento detectado", etc.
3. Registra ação no motor de suspeita (type="interact")

**Timeline:**
- Registra KILL event visível APENAS para o assassino (visible_to=[assassin_id])

**Retorno:** `{success: true, delay: X}` ou erro

#### 4.5.2 Processamento de Kills Pendentes (process_pending_kills)

Executado a cada 0.5 segundos (game tick loop):

1. Para cada PendingKill onde `now >= execute_at`:
   a. Muda status do alvo para DEAD
   b. Incrementa kills do assassino
   c. Registra DEATH na timeline
   d. Atualiza suspeita: para cada ator nos últimos 10s de eventos, incrementa temporal_score em +0.3
   e. Verifica look patterns: quem olhou para a vítima recentemente e ela morreu = look_pattern_score +0.35
   f. Adiciona à lista de mortes executadas

2. **Condição de vitória:** Se não há mais vítimas ALIVE → end_game("assassin")

3. **Eventos aleatórios:** Se houve mortes, 15% chance de trigger blackout

#### 4.5.3 Investigação do Detetive (detective_investigate)

**Entrada:** detective_id, suspect_id

**Validações:**
1. Jogador deve ser DETECTIVE
2. Deve estar ALIVE
3. Deve ter has_power = true
4. Suspeito deve existir e estar ALIVE
5. Não pode investigar a si mesmo

**Cooldown:** DETECTIVE_COOLDOWN segundos

**Resultado — Evidência Ofuscada:**
- Pega score de suspeita do suspeito (nunca revela diretamente se é assassino)
- Classifica em níveis: "high" (≥0.7), "moderate" (≥0.4), "low" (≥0.15), "none" (<0.15)
- Gera hints textuais baseados nos sub-scores:
  - temporal_score > 0.3 → "Atividade próxima a mortes recentes"
  - activity_score > 0.3 → "Frequência de ações acima do normal"
  - look_pattern_score > 0.3 → "Padrão de olhar suspeito"
  - Se nenhum → "Sem evidências significativas"

**Timeline Context:**
- Busca últimos 5 eventos relacionados ao suspeito (INVESTIGATION_WINDOW = 15s)
- Inclui eventos de ruído com 30% de chance (some noise leaks through)
- Formato: tipo do evento + segundos atrás

**Retorno:**
```json
{
  "success": true,
  "evidence": {
    "player_id": "...",
    "level": "moderate",
    "score": 0.45,
    "hints": ["Atividade próxima a mortes recentes"],
    "recent_activity_count": 3,
    "timeline_snippets": [
      {"type": "look", "seconds_ago": 5.2, "data": {...}}
    ]
  }
}
```

#### 4.5.4 Acusação do Detetive (detective_accuse)

**Entrada:** detective_id, suspect_id

**Validações:** Mesmas da investigação (exceto cooldown — não tem)

**Se acusar CORRETAMENTE (suspeito é ASSASSIN):**
- Incrementa correct_accusations
- end_game("detective")
- Retorna: `{success: true, correct: true, message: "arrested", assassin_name: "..."}`

**Se acusar ERRADO:**
- Incrementa wrong_accusations
- Muda status do detetive para DEAD
- end_game("assassin_accuse")
- Retorna: `{success: true, correct: false, message: "died", accused_name: "...", assassin_name: "..."}`

> **IMPORTANTE:** Na implementação atual, errar uma acusação FAZ O DETETIVE MORRER e o ASSASSINO VENCE IMEDIATAMENTE. Isso é diferente da config "lose_power" — o código hardcoda a morte.

#### 4.5.5 Olhar (player_look)

**Entrada:** looker_id, target_id

**Validações:**
- Ambos devem estar ALIVE
- Não pode olhar para si mesmo

**Ação:**
1. Adiciona target_id ao looker.look_targets
2. Adiciona looker_id ao target.looked_at_by
3. Registra LOOK na timeline
4. Incrementa activity_score do looker em +0.05 (via suspicion.on_action("look"))

**Broadcast:** Notifica todos os jogadores sobre quem olhou para quem (informação social)

### 4.6 Eventos Especiais

#### Blackout
- `is_blackout = true` por BLACKOUT_DURATION segundos
- Interface escurece (overlay preto 85% opacidade com pulsação)
- Texto "⚡ APAGÃO!" / "⚡ BLACKOUT!" aparece
- Lógica continua normalmente, mas visualmente confuso

#### Check Blackout
- Verificado a cada tick: se `time_now >= blackout_end`, desativa

### 4.7 Cálculo de Tensão

```
death_ratio = 1 - (alive / total)
time_factor = min(1.0, elapsed / ROUND_DURATION)
tension = min(1.0, death_ratio * 0.6 + time_factor * 0.4)
```

A tensão é usada para:
- Cor vermelha gradual na borda da tela (CSS radial gradient com alpha = tension * 0.3)
- Sons de tensão em levels > 0.7

### 4.8 Serialização do Estado (get_state_for_player)

Cada jogador recebe um estado personalizado com as seguintes informações:

```json
{
  "room_code": "A1B2C3",
  "phase": "playing",
  "round": 1,
  "max_players": 6,
  "player_count": 6,
  "alive_count": 5,
  "tension": 0.35,
  "is_blackout": false,
  "me": { /* to_private_dict() — inclui role e icon real */ },
  "players": [ /* lista personalizada por perspectiva */ ],
  "winner": null,
  "is_creator": true,
  "time_elapsed": 45,
  "lang": "pt"
}
```

**Regras de visibilidade dos players:**
- Fase FINISHED: Todos veem todos os papéis e ícones reais
- Player é o próprio: Vê to_private_dict() + ícone do papel
- Player é detetive com poder: Vê to_detective_view() + ícone público (gênero)
- Outros: Veem to_public_dict() + ícone público (gênero)

**Se detetive com poder:** Estado inclui `suspicion_ranking` (rankeamento de suspeita)

**Eventos recentes:** Últimos 15 eventos visíveis ao jogador nos últimos 30 segundos

### 4.9 Estado do Lobby

```json
{
  "room_code": "A1B2C3",
  "phase": "lobby",
  "max_players": 6,
  "creator_id": "p_xxx",
  "players": [
    {"id": "...", "name": "...", "is_ai": false, "avatar_color": "#6C63FF", "gender": "m", "icon": "/images/JogadorMasculina.png"}
  ],
  "player_count": 3,
  "can_start": true,
  "lang": "pt"
}
```

### 4.10 GameManager
- Gerencia múltiplas salas em memória
- Cria salas com código aleatório de 6 caracteres hex
- CRUD: create_room, get_room, remove_room

---

## 5. SISTEMA DE EVENTOS E TIMELINE

### 5.1 Tipos de Evento (EventType)
```
KILL             # Assassino mata (hidden)
DEATH            # Jogador morre (broadcast)
LOOK             # Jogador olha para outro
INVESTIGATE      # Detetive investiga
ACCUSE           # Detetive acusa
CHAT             # Mensagem de chat
NOISE_LOOK       # Evento falso de "olhar"
NOISE_ACTIVITY   # Evento falso de atividade
BLACKOUT         # Início de apagão
INTERFERENCE     # Interferência nos dados
SUSPICION_CHANGE # Mudança de suspeita
PLAYER_JOIN      # Jogador entrou
PLAYER_LEAVE     # Jogador saiu
GAME_START       # Jogo iniciou
GAME_END         # Jogo terminou
ROUND_TICK       # Tick da rodada
TENSION          # Evento de tensão
```

### 5.2 Estrutura do Evento (GameEvent)
```
type: EventType
timestamp: float            # Unix timestamp
actor_id: string?           # Quem fez a ação
target_id: string?          # Alvo da ação
data: dict                  # Dados extras
visible_to: list[string]?   # null = todos, lista = específicos
is_noise: bool              # true se é evento falso/camuflagem
```

### 5.3 Queries da Timeline
- `get_recent(seconds)`: Eventos nos últimos N segundos
- `get_around_death(death_time, window=10)`: Eventos ±10s de uma morte (exclui KILL cru)
- `get_player_events(player_id, seconds=15)`: Eventos envolvendo um jogador
- `get_visible_to(player_id, seconds=15)`: Eventos visíveis para um jogador

### 5.4 Gerador de Ruído (NoiseGenerator)

**Mensagens de ruído (PT):**
```
"movimento detectado"
"olhar suspeito"
"atividade incomum"
"interação registrada"
"comportamento analisado"
"sinal captado"
```

**generate_noise(player_ids, count=2):**
- Gera `count` eventos falsos
- Cada evento usa ator e alvo aleatórios (diferentes)
- Tipo: NOISE_LOOK ou NOISE_ACTIVITY aleatório
- Timestamp: agora + offset aleatório 0.1 a 1.5 segundos
- is_noise = true

**should_trigger_blackout()**: `random() < 0.15`
**should_trigger_interference()**: `random() < 0.10`

---

## 6. MOTOR DE SUSPEITA — PSA (Percepção Social Artificial)

### 6.1 Perfil de Suspeita (SuspicionProfile)
Cada jogador tem 4 sub-scores:
```
base_score: float          # Base (0.0-1.0)
temporal_score: float      # Proximidade com mortes (0.0-1.0)
activity_score: float      # Frequência de ações (0.0-1.0)
look_pattern_score: float  # Padrões de olhar suspeitos (0.0-1.0)
```

**Cálculo do total:**
```
total = base * 0.1 + temporal * 0.4 + activity * 0.25 + look_pattern * 0.25
resultado = clamp(total, 0.0, 1.0)
```

**Pesos:** Temporal (40%) > Atividade (25%) = Padrão de olhar (25%) > Base (10%)

### 6.2 Decaimento
A cada chamada de decay():
```
elapsed = now - last_updated
decay = SUSPICION_DECAY * elapsed  (0.05 * elapsed)

temporal -= decay
activity -= decay * 0.5
look_pattern -= decay * 0.3
(todos com mínimo de 0.0)
```

### 6.3 Eventos que Alteram Suspeita

**on_death(victim_id, death_time, recent_actors):**
- Para cada ator nos eventos recentes: temporal_score += 0.3

**on_action(player_id, action_type):**
- "look": activity_score += 0.05
- "interact": activity_score += 0.1
- "reported": activity_score += 0.15, base_score += 0.1

**on_look_pattern(looker_id, target_id, target_died_soon):**
- Se target morreu logo após ser olhado: look_pattern_score += 0.35

### 6.4 Ranking
Ordena todos os perfis por total descendente:
```json
[
  {"player_id": "...", "suspicion": 0.65, "level": "moderate"},
  {"player_id": "...", "suspicion": 0.23, "level": "low"}
]
```

**Níveis de suspeita:**
- ≥ 0.7 → "high"
- ≥ 0.4 → "moderate"
- ≥ 0.15 → "low"
- < 0.15 → "none"

### 6.5 Evidência Ofuscada (para Detetive)
```json
{
  "player_id": "...",
  "level": "moderate",
  "score": 0.45,
  "hints": [
    "Atividade próxima a mortes recentes",
    "Frequência de ações acima do normal"
  ]
}
```
Hints são gerados baseados em sub-scores > 0.3.

---

## 7. SISTEMA DE IA (Bots)

### 7.1 Personalidades de IA (AIPersonality)
```
AGGRESSIVE  — Mata rápido, escolha aleatória, ações frequentes
CAUTIOUS    — Mata devagar (50% chance de skip), cauteloso
ERRATIC     — Comportamento imprevisível
CALCULATED  — Evita matar quem olhou recentemente
```

### 7.2 Nomes de Bots
```
Shadow, Phantom, Cipher, Echo, Specter,
Raven, Onyx, Viper, Storm, Ghost,
Nyx, Blade, Ember, Frost, Nebula
```

### 7.3 Comportamento do Bot — Loop Principal
O bot executa um loop assíncrono contínuo:

1. **Espera o jogo iniciar** (enquanto fase = lobby)
2. **Enquanto fase = playing e bot está ALIVE:**
   a. Decide e age (think_and_act)
   b. Espera delay aleatório: AI_THINK_DELAY_MIN a AI_THINK_DELAY_MAX (1.5-5.0s)

### 7.4 Bot como Assassino
1. **Blefe (60% chance):** Olha para um jogador aleatório (cria ruído social)
2. **Verificação de kill:** Se tempo desde última ação >= threshold aleatório (8-18s):
   - Escolhe alvo baseado na personalidade (exclui detetive dos alvos):
     - AGGRESSIVE: aleatório
     - CALCULATED: evita quem olhou recentemente (últimos 3 looks)
     - CAUTIOUS: 50% chance de skip
     - ERRATIC: aleatório
   - Executa kill
   - **Desvio de atenção:** Olha para outro jogador diferente do alvo

### 7.5 Bot como Detetive
1. **Olhar (50% chance):** Olha para jogador aleatório
2. **Investigação:** Se tempo desde última ação >= threshold (10-20s):
   - Busca ranking de suspeita
   - Investiga o jogador mais suspeito
   - **Acusação automática:** Se evidência = "high" E já fez ≥2 investigações E random < 0.6 → acusa

3. **Sem poder:** Se perdeu o poder, apenas olha

### 7.6 Bot como Vítima
- 40% chance de olhar para jogador aleatório a cada ciclo
- Comportamento simples para criar ruído social

### 7.7 AIManager — Gestão de Bots

**fill_room(room):**
- Preenche slots vazios com bots até max_players
- Cada bot recebe nome único da lista AI_NAMES
- Se nomes acabarem, usa "Bot-N"
- Gênero aleatório ("m" ou "f")

**replace_player(room, leaving_player_id):**
- Se jogador está morto: apenas remove o jogador
- Se jogador está vivo:
  1. Cria novo bot com ID `ai_XXXXXXXX`
  2. Copia role e status do jogador que saiu
  3. Nome: `"NomeOriginal (Bot)"`
  4. Remove jogador original
  5. Adiciona bot
  6. Se jogo está em andamento, inicia loop do bot
  7. Retorna ID do novo bot

**start_bots(room_code):** Inicia loop de todos os bots da sala
**stop_bots(room_code):** Para todos os bots da sala

---

## 8. CONDIÇÕES DE VITÓRIA

```
winner = "assassin"       → Assassino matou todas as vítimas
winner = "detective"      → Detetive acusou o assassino corretamente
winner = "assassin_accuse" → Detetive acusou a pessoa errada (detetive morre)
winner = "detective_auto"  → Assassino tentou matar o detetive (detetive vence automaticamente)
```

---

## 9. COMUNICAÇÃO EM TEMPO REAL (WebSocket)

### 9.1 ConnectionManager
Gerencia conexões WebSocket agrupadas por sala:
- Estruturas: `rooms[room_code][player_id] = WebSocket`, `player_rooms[player_id] = room_code`, `connections[player_id] = WebSocket`

**Operações:**
- `connect(ws, room_code, player_id)`
- `disconnect(player_id, ws?)` — Se WS fornecido, só desconecta se é o WS armazenado (evita race condition no reload)
- `send_to_player(player_id, data)` — Mensagem individual
- `broadcast_to_room(room_code, data, exclude?)` — Mensagem para toda sala
- `broadcast_state(room_code, game_room)` — Estado personalizado para cada jogador

### 9.2 Endpoint WebSocket
`/ws/{room_code}/{player_id}`

**Conexão:**
1. Valida que sala e jogador existem (senão fecha com código 4001)
2. Cancela timer de reconexão pendente (se existir)
3. Conecta ao manager
4. Envia estado inicial (lobby_update ou state_update dependendo da fase)
5. Configura callbacks de broadcast para IA

### 9.3 Grace Period de Reconexão
Quando um jogador desconecta durante o jogo:
1. **NÃO substitui imediatamente por IA**
2. Agenda task assíncrona com delay de **8 segundos**
3. Após 8s, se jogador não reconectou:
   - Substitui por IA (mantendo papel e estado)
   - Broadcast "player_replaced"
4. Se jogador reconecta dentro de 8s:
   - Cancela o timer
   - Mantém configuração original

### 9.4 Tipos de Mensagem do Cliente → Servidor

```
start_game     — Criador inicia o jogo
fill_ai        — Criador preenche com IA
kick_ai        — Criador remove um bot do lobby
                 Body: {target_id: "ai_xxx"}
kill           — Assassino mata
                 Body: {target_id: "p_xxx"}
investigate    — Detetive investiga
                 Body: {target_id: "p_xxx"}
accuse         — Detetive acusa
                 Body: {target_id: "p_xxx"}
look           — Qualquer jogador olha
                 Body: {target_id: "p_xxx"}
chat           — Mensagem de chat
                 Body: {message: "texto"}
victim_report  — Vítima reporta comportamento suspeito
                 Body: {target_id: "p_xxx", reason: "texto"}
victim_hint    — Vítima envia dica ao detetive
                 Body: {target_id: "p_xxx", hint: "texto"}
play_again     — Criador reinicia rodada
leave_game     — Jogador sai voluntariamente
ping           — Keep-alive
```

### 9.5 Tipos de Mensagem do Servidor → Cliente

```
state_update           — Estado personalizado do jogo
                         Body: {state: {...}}
lobby_update           — Estado do lobby
                         Body: {state: {...}}
game_started           — Jogo iniciou (redirect para tela de jogo)
                         Body: {redirect: "/game/ROOM"}
kill_result            — Resultado do kill para o assassino
                         Body: {result: {success, delay?, error?, remaining?}}
investigate_result     — Resultado da investigação para detetive
                         Body: {result: {success, evidence: {...}}}
accusation             — Acusação feita (broadcast)
                         Body: {detective_id, suspect_id, correct, message}
look_event             — Alguém olhou para outro (broadcast)
                         Body: {actor_id, actor_name, target_id, target_name}
chat_message           — Mensagem de chat (broadcast)
                         Body: {player_id, player_name, message, avatar_color, icon}
victim_report_broadcast — Report de vítima (broadcast)
                         Body: {reporter_id, reporter_name, target_id, target_name, reason, icon}
victim_hint            — Dica de vítima (APENAS para o detetive)
                         Body: {from_id, from_name, target_id, target_name, hint, icon}
hint_sent              — Confirmação de dica enviada (para quem enviou)
game_restarted         — Nova rodada iniciada
player_replaced        — Jogador substituído por IA
                         Body: {old_id, new_id}
accuse_error           — Erro na acusação
                         Body: {result: {error: "..."}}
ai_action              — Ação de bot (broadcast)
                         Body: {actor_id, action, target_id}
pong                   — Resposta ao ping
```

### 9.6 Handlers Detalhados

**_handle_victim_report:**
1. Valida que jogador é vítima ALIVE
2. Sanitiza reason (remove `<>`, máx 200 chars)
3. Incrementa suspeita do alvo (on_action(target_id, "reported"))
4. Broadcast victim_report_broadcast para toda sala

**_handle_victim_hint:**
1. Valida que jogador é vítima ALIVE
2. Sanitiza hint (remove `<>`, máx 200 chars)
3. Encontra o detetive na sala
4. Envia hint APENAS para o detetive (send_to_player)
5. Envia confirmação hint_sent para a vítima

**_handle_chat:**
1. Valida que jogador existe e NÃO está morto (mortos não podem falar)
2. Sanitiza mensagem (remove `<>`, máx 200 chars)
3. Broadcast para toda sala com player_name, avatar_color, icon

**_handle_play_again:**
1. Verifica que é o criador da sala
2. Chama room.reset_for_new_round()
3. Reinicia bots
4. Reinicia game tick loop
5. Broadcast game_restarted + state_update

**_handle_leave_game:**
1. Cancela timers de desconexão pendentes
2. Se PLAYING: substitui por IA imediatamente
3. Se LOBBY: remove jogador

### 9.7 Game Tick Loop
Background loop a cada 0.5 segundos:
1. Processa kills pendentes
2. Verifica blackout
3. Se houve mortes OU jogo terminou: broadcast state
4. Se jogo terminou: para bots

---

## 10. ROTAS HTTP

### 10.1 Página Inicial
`GET /` → index.html
- Parâmetros: lang (default "pt")
- Formulário para criar sala ou entrar em sala existente

### 10.2 Criar Sala
`POST /create-room`
- Form data: player_name, max_players, lang, gender
- Sanitiza nome (máx 20 chars, remove `<>&"'`)
- Gera player_id único: `p_{uuid_hex[:10]}`
- Cria sala via GameManager
- Redireciona para `/lobby/{room_code}?pid={player_id}&lang={lang}`

### 10.3 Entrar em Sala
`POST /join-room`
- Form data: player_name, room_code, lang, gender
- Sanitiza: nome, código (uppercase, apenas alfanumérico)
- **Se jogo em andamento:** Tenta substituir um bot IA pelo jogador humano
  - Copia role, status, avatar_color do bot
  - Remove bot do AIManager
  - Redireciona para `/game/{room_code}?pid={player_id}&lang={lang}`
- **Se lobby:** Adiciona jogador normalmente
- Erros: sala não encontrada, sala cheia, jogo já iniciado (sem bots)

### 10.4 Lobby
`GET /lobby/{room_code}?pid={player_id}&lang={lang}`
- Valida que sala existe
- Renderiza lobby.html com estado da sala

### 10.5 Tela de Jogo
`GET /game/{room_code}?pid={player_id}&lang={lang}`
- Valida que sala existe E jogador está na sala
- Renderiza game.html com room_code, player_id, lang, translations, config

---

## 11. INTERFACE DO CLIENTE (JavaScript)

### 11.1 Inicialização
```javascript
initGame({roomCode, playerId, lang, translations, config})
```
- Carrega histórico do chat do sessionStorage
- Mostra loading
- Conecta WebSocket
- Configura atalhos de teclado
- Inicia ticker de cooldown (a cada 1s)

### 11.2 WebSocket do Cliente
- Protocolo: `ws://` ou `wss://`
- URL: `${proto}//${host}/ws/${ROOM_CODE}/${PLAYER_ID}`
- Keep-alive: Ping a cada 25 segundos
- Reconexão automática: Após 2 segundos em caso de desconexão
- Código 4001: Redireciona para página inicial (jogador não encontrado)

### 11.3 Persistência de Chat
- Chave: `chat_history_${ROOM_CODE}` no sessionStorage
- Salva array de mensagens: `{name, color, text, icon}`
- Carrega e recria bolhas ao reconectar
- Limpa ao iniciar nova rodada (game_restarted)

### 11.4 Renderização do Jogo (renderGame)
Sempre renderiza (não importa a fase):
1. Header (papel, rodada, jogadores vivos, tensão)
2. Círculo de jogadores
3. Barra de ações
4. Overlay de tensão
5. Overlay de blackout
6. Eventos recentes
7. Se fase = finished: Overlay de Game Over (POR CIMA de tudo)

### 11.5 Círculo de Jogadores
Cada jogador renderizado como "node" com:
- Avatar colorido com ícone (role-based para si, gender-based para outros)
- Nome + badge de IA (🤖)
- Barra de suspeita (apenas para detetive com poder)
- Indicador de seleção (borda cyan com glow)
- Indicador de morto (opacity 0.35, sem pointer-events)
- Indicador do próprio jogador (borda purple)
- Classes de suspeita: suspect-high (glow vermelho), suspect-moderate (glow laranja)

**Interação:** Clicar em outro jogador seleciona como alvo (toggle)

### 11.6 Barra de Ações
Renderizada conforme o papel do jogador:

**Assassino:**
- 🔪 Kill (com cooldown visual)
- 👁️ Olhar para

**Detetive (com poder):**
- 🔍 Investigar (com cooldown visual)
- ⚖️ Acusar (com confirm dialog)
- 👁️ Olhar para

**Detetive (sem poder):**
- ❌ "Você perdeu seus poderes!"

**Vítima:**
- 🚨 Reportar (abre modal com opções predefinidas)
- 💡 Dica p/ Detetive (abre modal com opções + texto livre)
- 👁️ Olhar para

**Morto:**
- 💀 Espectador

**Todos os botões requerem alvo selecionado (exceto chat)**

### 11.7 Sistema de Report de Vítima

**Opções predefinidas (PT):**
```
"Está agindo de forma suspeita"
"Estava olhando muito para alguém"
"Evita contato visual"
"Comportamento estranho após uma morte"
"Parece nervoso(a)"
```

**Opções predefinidas (EN):**
```
"Acting suspiciously"
"Staring at someone a lot"
"Avoiding eye contact"
"Strange behavior after a death"
"Seems nervous"
```

**Fluxo:**
1. Selecionar alvo → Clicar "🚨 Reportar"
2. Modal abre com opções
3. Clicar em opção → Envia victim_report ao servidor
4. Servidor: incrementa suspeita do alvo, broadcast para todos
5. Aparece no chat como mensagem de sistema verde: `🚨 REPORTE: Nome → Alvo: "Motivo"`

### 11.8 Sistema de Dica para Detetive

**Opções predefinidas (PT):**
```
"Acho que essa pessoa é o assassino"
"Essa pessoa está agindo de forma estranha"
"Essa pessoa evita contato visual"
"Vi algo suspeito sobre essa pessoa"
"Fique de olho nessa pessoa"
```

**+ Campo de texto livre (máx 200 chars)**

**Fluxo:**
1. Selecionar alvo → Clicar "💡 Dica p/ Detetive"
2. Modal abre com opções predefinidas + input customizado
3. Enviar → victim_hint ao servidor
4. Servidor: Envia APENAS ao detetive
5. Detetive vê no chat: `💡 DICA (NomeDaVítima): "texto" sobre NomeDoAlvo`
6. Detetive também vê toast temporário

### 11.9 Painel de Investigação
Aparece quando detetive recebe resultado de investigação:
- Mostra nome do suspeito
- Nível de suspeita com cor (high=red, moderate=orange, low=green, none=gray)
- Score numérico
- Hints textuais (lista)
- Timeline snippets (tipo + segundos atrás)
- Auto-esconde após 10 segundos

### 11.10 Tela de Game Over
Overlay com:
- Título: "🕵️ O Detetive venceu!" ou "🔪 O Assassino venceu!"
- Mensagem contextual:
  - detective: "Detetive X prendeu o Assassino Y"
  - detective_auto: "Detetive venceu, pois Assassino tentou matá-lo"
  - assassin_accuse: "Detetive acusou a pessoa errada. O Assassino era X"
  - assassin: "Assassino X matou todas as vítimas"
- Lista com todos os jogadores mostrando papéis revelados, ícones e status
- Botão "🔄 Jogar Novamente" (apenas para criador)
- Botão "🚪 Sair" (todos)
- Mensagem "Aguardando o anfitrião..." (não-criadores)

### 11.11 Cooldown Visual
- Timer decrementando a cada 1 segundo
- Badge no canto do botão mostrando segundos restantes
- Botão desabilitado durante cooldown

### 11.12 Atalhos de Teclado
```
K — Kill (assassino)
I — Investigar (detetive)
L — Olhar
C — Toggle chat
Esc — Deselecionar alvo + fechar painel de investigação
Enter (no chat input) — Enviar mensagem
```

---

## 12. SISTEMA DE ÁUDIO (Web Audio API)

Todos os sons são gerados proceduralmente via Web Audio API — ZERO arquivos de áudio externos.

### Sons disponíveis:
```
death:      200Hz sawtooth 0.8s + 120Hz sawtooth 1.2s (com delay)
kill:       800Hz square 0.15s + 400Hz square 0.3s
investigate: 600Hz sine 0.2s + 900Hz sine 0.3s
accuse:     500Hz sawtooth 0.15s + 700Hz + 1000Hz (escala)
success:    523Hz + 659Hz + 784Hz sine (C-E-G chord ascending)
error:      300Hz square 0.3s + 200Hz square 0.5s
look:       1200Hz sine 0.08s (som rápido sutil)
chat:       1000Hz sine 0.05s (notificação sutil)
blackout:   80Hz sawtooth 2.0s + 60Hz sawtooth 1.5s (grave ameaçador)
tension:    100Hz sine 3.0s (drone de tensão)
gameOver:   400→350→300→200Hz sine (escala descendente triste)
victory:    523→659→784→1047Hz sine (C-E-G-C alto, fanfarra)
```

**Implementação:** Cada som usa OscillatorNode + GainNode com rampa exponencial de volume para zero. Volumes baixos (0.03-0.15) para não assustar.

---

## 13. DESIGN VISUAL (CSS)

### 13.1 Tema
- **Fundo:** `#0a0a1a` (quase preto com tom azul)
- **Cards:** `#16163a` (azul escuro)
- **Fontes:** Inter (principal), Fira Code (mono/código)
- **Raios de borda:** 12px (padrão), 8px (pequeno), 50% (circular)

### 13.2 Cores de Destaque (Neon)
```
Purple:  #6C63FF  (botões primários, destaque)
Pink:    #FF6584  (botões secundários)
Green:   #43E97B  (sucesso, vítima)
Orange:  #F7971E  (acusação, suspeita moderada)
Cyan:    #00C9FF  (detetive, informação)
Red:     #FF4444  (assassino, erro, perigo)
```

### 13.3 Efeitos Visuais
- **Glitch:** Título na página inicial com efeito de falha digital (CSS clip-path + translate animation)
- **Partículas:** Background animado na página inicial (pequenos pontos subindo)
- **Glow:** Botões com after pseudo-element com blur
- **Pulse ring:** Animação de espera no lobby (anel pulsante)
- **Tensão:** Overlay vermelho radial com intensidade proporcional à tensão

### 13.4 Responsividade
- **Mobile-first** (< 380px, < 480px, ≥ 640px, ≥ 1024px)
- **Meta viewport:** width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no
- **Chat mobile (< 480px):** Posicionado no topo (abaixo do header), full width
- **Chat desktop:** Fixo bottom-right, 320px de largura
- **Evento log mobile (< 380px):** Escondido

### 13.5 Elementos Principais

**Header:**
- Badge do código da sala
- Badge da rodada
- Revelação do papel (com cor e ícone)
- Badge de jogadores vivos
- Barra de tensão (gradient green→orange→red)
- Botão de sair (✕)

**Player Circle:**
- Flex wrap centralizado, max-width 600px
- Nodes com 75px min-width (60px em <380px)
- Avatares 48px (38px em <380px)

**Action Bar:**
- Flex wrap centralizado no footer
- Botões com border-radius 20px (pill shape)
- Cada tipo com cor temática

**Chat Panel:**
- Fixed bottom-right (desktop) ou top full-width (mobile)
- Toggle com badge de não-lidos
- Mensagens com ícone + nome colorido + texto
- Input com border-radius 20px

**Modais (Report/Hint):**
- Overlay escuro (70% opacidade)
- Card centralizado, max-width 400px
- Opções como botões de lista

---

## 14. TRADUÇÕES (i18n)

Dois idiomas suportados: PT e EN. Todas as strings da interface:

```
game_title:        "Assassino da Piscada" / "Blink Assassin"
create_room:       "Criar Sala" / "Create Room"
join_room:         "Entrar na Sala" / "Join Room"
your_name:         "Seu Nome" / "Your Name"
room_code:         "Código da Sala" / "Room Code"
players:           "Jogadores" / "Players"
start_game:        "Iniciar Jogo" / "Start Game"
waiting:           "Aguardando jogadores..." / "Waiting for players..."
you_are:           "Você é" / "You are"
assassin:          "Assassino" / "Assassin"
detective:         "Detetive" / "Detective"
victim:            "Vítima" / "Victim"
dead:              "Morto" / "Dead"
alive:             "Vivo" / "Alive"
spectator:         "Espectador" / "Spectator"
kill:              "Eliminar" / "Eliminate"
investigate:       "Investigar" / "Investigate"
accuse:            "Acusar" / "Accuse"
look_at:           "Olhar para" / "Look at"
chat:              "Chat" / "Chat"
send:              "Enviar" / "Send"
died:              "morreu!" / "died!"
arrested:          "Preso em nome da lei!" / "Arrested in the name of the law!"
assassin_wins:     "O Assassino venceu!" / "The Assassin wins!"
detective_wins:    "O Detetive venceu!" / "The Detective wins!"
wrong_accusation:  "Acusação errada!" / "Wrong accusation!"
cooldown_active:   "Aguarde o cooldown..." / "Cooldown active..."
suspicious_activity: "Atividade suspeita detectada" / "Suspicious activity detected"
no_evidence:       "Sem evidências claras" / "No clear evidence"
high_suspicion:    "Alta probabilidade" / "High probability"
moderate_suspicion: "Comportamento suspeito" / "Suspicious behavior"
blackout:          "⚡ APAGÃO!" / "⚡ BLACKOUT!"
interference:      "📡 Interferência nos dados!" / "📡 Data interference!"
game_over:         "Fim de Jogo" / "Game Over"
play_again:        "Jogar Novamente" / "Play Again"
ai_player:         "Bot" / "Bot"
room_full:         "Sala cheia" / "Room full"
copied:            "Copiado!" / "Copied!"
round:             "Rodada" / "Round"
time_left:         "Tempo restante" / "Time left"
players_alive:     "Jogadores vivos" / "Players alive"
tension_rising:    "A tensão aumenta..." / "Tension is rising..."
someone_died:      "Alguém morreu..." / "Someone died..."
look_registered:   "Olhar registrado" / "Look registered"
power_lost:        "Você perdeu seus poderes!" / "You lost your powers!"
fill_with_ai:      "Completar com IA" / "Fill with AI"
```

---

## 15. FLUXO COMPLETO DE UMA PARTIDA

### 15.1 Criação de Sala
1. Jogador acessa página inicial → Informa nome, gênero, quantidade de jogadores
2. Clica "Criar Sala" → POST /create-room → Redireciona para lobby
3. Recebe código de 6 caracteres (ex: "A1B2C3") para compartilhar

### 15.2 Entrada na Sala
1. Outro jogador acessa página inicial → Informa nome, gênero, código da sala
2. Clica "Entrar na Sala" → POST /join-room → Redireciona para lobby
3. Se jogo em andamento e há bot: substitui bot pelo humano, vai direto para o jogo

### 15.3 Lobby
1. WebSocket conecta para receber atualizações em tempo real
2. Grid mostra jogadores presentes (com avatar, nome, badge de IA ou host)
3. Criador pode: "Completar com IA" (preenche slots vazios com bots)
4. Criador pode remover bots individualmente (botão ✕ no slot)
5. Criador clica "Iniciar Jogo" (requer mínimo 3 jogadores)
6. Broadcast game_started → Todos redirecionam para /game/{room_code}

### 15.4 Gameplay
1. WebSocket conecta, recebe state_update com papel revelado
2. **Game tick loop** roda no servidor a cada 0.5s processando kills e blackouts
3. Jogadores interagem: olhar, matar, investigar, acusar, reportar, dar dica, chat
4. Mortes acontecem com delay (2-8s) e camuflagem por eventos falsos
5. Detetive investiga usando evidência ofuscada (nunca 100% claro)
6. Tensão aumenta gradualmente (visual vermelho + sons)
7. Blackouts podem ocorrer após mortes (15% chance)

### 15.5 Fim de Jogo
1. Uma condição de vitória é atingida (ver seção 8)
2. Todos os papéis são revelados com ícones reais
3. Overlay mostra resultado, estatísticas, lista de jogadores com papéis
4. Criador pode clicar "Jogar Novamente" → nova rodada com papéis reshuffled
5. Qualquer um pode "Sair" → volta à página inicial

### 15.6 Reconexão
1. Se WebSocket desconecta (reload de página, perda de rede)
2. Cliente tenta reconectar após 2 segundos
3. Servidor aguarda 8 segundos antes de substituir por IA
4. Se reconectar a tempo: jogador mantém tudo normalmente
5. Chat histórico é restaurado do sessionStorage

---

## 16. SEGURANÇA E VALIDAÇÃO

### 16.1 Validação de Input
- Nomes: máx 20 chars, remoção de `<>&"'`
- Mensagens de chat: máx 200 chars, remoção de `<>`
- Reports e hints: máx 200 chars, remoção de `<>`
- Room codes: uppercase, apenas alfanumérico, máx 6 chars
- Gênero: apenas "m" ou "f"
- max_players: limitado entre MIN_PLAYERS e MAX_PLAYERS

### 16.2 Validação no Servidor
- Todas as ações são validadas no servidor (anti-cheat)
- Cooldowns enforced no servidor
- Papéis verificados antes de cada ação
- Status ALIVE verificado antes de ações
- Auto-targeting impedido (não pode matar/investigar a si mesmo)
- Mortos não podem enviar chat
- Broadcast de estado personalizado (cada jogador vê apenas o que deveria)

### 16.3 Race Conditions
- Disconnect do WebSocket verifica se é a conexão atual (evita remover conexão mais nova)
- Timer de reconexão cancelado se jogador reconecta a tempo

---

## 17. ARQUITETURA SUGERIDA PARA .NET MAUI

### 17.1 Opção Recomendada: Embedded Server + Client

A aplicação MAUI funciona tanto como **servidor** (host da partida) quanto como **cliente** (jogador).

**Dispositivo que cria a sala:**
- Roda um servidor WebSocket embarcado (ex: usando ASP.NET Core Kestrel mínimo ou WebSocket puro)
- Toda a lógica do jogo roda neste device
- IP local + porta compartilhados para outros jogadores

**Dispositivos que entram na sala:**
- Conectam via WebSocket ao dispositivo host
- Apenas enviam ações e recebem estado

### 17.2 Estrutura de Projeto Sugerida

```
DAGroup.MAUI/
├── App.xaml + App.xaml.cs
├── AppShell.xaml
├── MauiProgram.cs
├── Models/
│   ├── Player.cs
│   ├── GameRoom.cs
│   ├── GameConfig.cs
│   ├── GameEvent.cs
│   ├── SuspicionProfile.cs
│   └── Enums.cs (RoleType, PlayerStatus, GamePhase, EventType, AIPersonality)
├── Services/
│   ├── GameEngine.cs          # Lógica do jogo (port do engine.py)
│   ├── SuspicionEngine.cs     # Motor de suspeita (port do suspicion.py)
│   ├── EventTimeline.cs       # Timeline + NoiseGenerator (port do events.py)
│   ├── AIManager.cs           # Sistema de IA (port do ai.py)
│   ├── WebSocketServer.cs     # Servidor WebSocket embarcado
│   ├── WebSocketClient.cs     # Cliente WebSocket
│   ├── ConnectionManager.cs   # Gerenciador de conexões
│   ├── AudioService.cs        # Sons procedurais (SKAudioPlayer ou AudioGraph)
│   └── TranslationService.cs  # i18n PT/EN
├── ViewModels/
│   ├── HomeViewModel.cs
│   ├── LobbyViewModel.cs
│   └── GameViewModel.cs
├── Views/ (Pages)
│   ├── HomePage.xaml           # Criar/Entrar sala
│   ├── LobbyPage.xaml          # Lobby com grid de jogadores
│   └── GamePage.xaml           # Tela principal do jogo
├── Controls/
│   ├── PlayerCircle.xaml       # Componente do círculo de jogadores
│   ├── ActionBar.xaml          # Barra de ações
│   ├── ChatPanel.xaml          # Painel de chat
│   ├── InvestigationPanel.xaml # Painel de investigação
│   └── GameOverOverlay.xaml    # Overlay de fim de jogo
├── Resources/
│   ├── Images/                 # Assassino.png, Detetive.png, etc.
│   ├── Styles/                 # Estilos MAUI (dark theme)
│   └── Fonts/                  # Inter, Fira Code
├── Platforms/
│   └── Android/
│       └── AndroidManifest.xml (permissões: INTERNET, ACCESS_WIFI_STATE)
```

### 17.3 Padrão MVVM
- **Models:** Dados puros (Player, GameRoom, etc.)
- **Services:** Lógica de negócio (GameEngine, SuspicionEngine, AI)
- **ViewModels:** Binding entre UI e lógica (INotifyPropertyChanged)
- **Views:** XAML com bindings
- **Dependency Injection:** Registrar services no MauiProgram.cs

### 17.4 Considerações Android
- Permissões: INTERNET, ACCESS_WIFI_STATE, ACCESS_NETWORK_STATE
- Background service para manter servidor WebSocket ativo
- Vibração para notificações (morte, acusação)
- Manter tela ligada durante gameplay (Wakelock)
- Shared Preferences para configurações persistentes
- Handling de app lifecycle (pause/resume → reconexão WebSocket)

---

## 18. PONTOS CRÍTICOS PARA IMPLEMENTAÇÃO

1. **Timer system:** Uso de async/await com CancellationToken para kills pendentes, cooldowns, e decisões de IA
2. **Concorrência:** Thread-safe access para state mutations (lock/semaphore)
3. **WebSocket reliability:** Reconnection com exponential backoff, ping/pong
4. **State broadcast personalizado:** Cada jogador deve receber estado próprio (papel oculto)
5. **Kill delay:** O delay de 2-8 segundos é FUNDAMENTAL para a mecânica do jogo — não pode ser instantâneo
6. **Noise generation:** Eventos falsos são gerados a CADA kill para esconder a ação
7. **Suspicion never reveals directly:** O sistema NUNCA diz "esse cara é o assassino" — sempre probabilístico
8. **Dead players:** Não podem agir (chat, look, report) mas podem observar
9. **AI replacement:** Deve ser transparente — o bot assume o papel exato do jogador que saiu
10. **Chat persistence:** Essencial para a experiência — deve sobreviver a reconexões

---

## 19. STACK TECNOLÓGICA MAUI

```
Framework:     .NET 9 + MAUI
Linguagem:     C# 13
UI:            XAML + MVVM
WebSocket:     System.Net.WebSockets (client) + WebSocketSharp ou Fleck (server)
Audio:         Plugin.Maui.Audio ou SkiaSharp.Audio
DI:            Microsoft.Extensions.DependencyInjection (built-in)
Serialização:  System.Text.Json
Async:         Task/async-await + CancellationToken
Timer:         System.Threading.Timer ou PeriodicTimer
Preferences:   Microsoft.Maui.Storage.Preferences
Build APK:     dotnet publish -f net9.0-android -c Release
```

---

## 20. RESUMO DAS PALAVRAS-CHAVE DE BUSCA

Se precisar encontrar algo neste documento:
- **Regras de vitória** → Seção 8
- **Como kill funciona** → Seção 4.5.1 e 4.5.2
- **Investigação do detetive** → Seção 4.5.3
- **Sistema de suspeita PSA** → Seção 6
- **Comportamento da IA** → Seção 7
- **Mensagens WebSocket** → Seção 9.4 e 9.5
- **Interface/UI** → Seção 11, 13
- **Sons** → Seção 12
- **Traduções** → Seção 14
- **Fluxo completo** → Seção 15
- **Arquitetura MAUI** → Seção 17

---

## 21. CHECKLIST DE IMPLEMENTAÇÃO

### MVP (Mínimo Viável)
- [ ] Modelos: Player, GameRoom, Enums
- [ ] GameEngine: criar sala, atribuir papéis, iniciar jogo
- [ ] Kill com delay + processamento de kills pendentes
- [ ] Investigação com evidência ofuscada
- [ ] Acusação com consequências (correto = vitória, errado = morte)
- [ ] Sistema de olhar (look)
- [ ] WebSocket server embarcado
- [ ] WebSocket client com reconexão
- [ ] Página inicial (criar/entrar sala)
- [ ] Lobby com grid de jogadores
- [ ] Tela de jogo com círculo de jogadores
- [ ] Barra de ações (kill, investigate, accuse, look)
- [ ] Chat em tempo real
- [ ] Game over com revelação de papéis
- [ ] Tradução PT/EN

### Fase 2 (Completo)
- [ ] Motor de suspeita PSA (4 camadas)
- [ ] Geração de ruído (eventos falsos)
- [ ] Blackout e interferência
- [ ] IA com 4 personalidades
- [ ] Preenchimento automático com IA
- [ ] Substituição de jogador por IA
- [ ] Report de vítima + hint ao detetive
- [ ] Chat com persistência
- [ ] Overlay de tensão visual
- [ ] Sons procedurais
- [ ] Cooldowns visuais
- [ ] Atalhos de teclado (ou gestos em mobile)
- [ ] Grace period na reconexão (8s)
- [ ] Mid-game join (substituir bot por humano)

### Fase 3 (Polish)
- [ ] Animações (morte, acusação, seleção)
- [ ] Vibração em eventos importantes
- [ ] Efeito glitch no título
- [ ] Partículas de fundo
- [ ] Tema escuro com neon
- [ ] Responsividade (tablet + phone)
- [ ] APK assinado para distribuição

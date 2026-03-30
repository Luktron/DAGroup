The user wants me to create a comprehensive Markdown document called "MAUI_DAG.md" that describes all the logic, functionalities, and rules of the current application so that another LLM agent can recreate it as a .NET MAUI application (to generate an APK).

I need to thoroughly analyze the entire codebase to document everything accurately. Let me read all the key files to understand every mechanic, rule, and feature.

Let me first gather the complete codebase to document everything accurately.

Now let me also check the remaining parts of config.py and game.js:

Now let me check the remaining part of the _handle_victim_hint and _handle_victim_report handlers:

Now let me check the CSS file for the complete styling reference:

Read style.css, lines 1 to 1200

Now I have a thorough understanding of the entire codebase. Let me also check for avatar icon images:

Now I have everything needed. Let me create the comprehensive MAUI specification document. I'm in Ask mode and cannot create files directly. I'll provide the complete Markdown document content for you to create as MAUI_DAG.md in your project root:

# MAUI_DAG — Assassino da Piscada (.NET MAUI)

## Especificação Completa para Recriação em .NET MAUI

> Este documento descreve **toda a lógica, funcionalidades, regras e arquitetura** da aplicação web "Assassino da Piscada" (Python/FastAPI/WebSocket) para que um agent LLM possa recriá-la como aplicação .NET MAUI nativa gerando APK Android.

---

## 1. VISÃO GERAL

**Nome:** Assassino da Piscada (Blink Assassin)  
**Tipo:** Jogo multiplayer social de dedução em tempo real  
**Idiomas:** Português (PT) e Inglês (EN) — bilíngue  
**Plataforma alvo:** Android APK via .NET MAUI  
**Jogadores:** Mínimo 3, máximo 12, padrão 6  
**Comunicação:** WebSocket em tempo real (< 200ms)  

### Conceito
Baseado no jogo presencial onde um assassino elimina vítimas "piscando" e um detetive tenta identificá-lo. Na versão digital, a "piscada" é substituída por ação secreta no servidor com delay aleatório e eventos de ruído para camuflar.

---

## 2. PAPÉIS (ROLES)

### 2.1 Assassino (Assassin)
- **Ícone:** `Assassino.png`
- **Cor temática:** Vermelho (`#FF4444`)
- **Ações:**
  - **Eliminar (Kill)** — selecionar alvo vivo → ação secreta → morte com delay aleatório de 2-8 segundos
  - **Olhar (Look)** — olhar para qualquer jogador vivo (ação social, gera dados rastreáveis)
  - **Chat** — enviar mensagens para todos
- **Cooldown de kill:** 10 segundos entre eliminações
- **Restrição CRÍTICA:** NÃO pode matar o Detetive. Se tentar, o Detetive vence automaticamente (`detective_auto` win)
- **Condição de vitória:** Matar todas as vítimas (detetive vivo não impede vitória)
- **Tecla de atalho:** K

### 2.2 Detetive (Detective)
- **Ícone:** `Detetive.png`
- **Cor temática:** Ciano (`#00C9FF`)
- **Ações:**
  - **Investigar (Investigate)** — analisa um jogador, recebe evidências ofuscadas (nunca 100% claras)
  - **Acusar (Accuse)** — acusar um jogador de ser o assassino. Alto risco:
    - Se correto → Detetive vence (`detective` win)
    - Se errado → O jogo acaba imediatamente com vitória do Assassino (`assassin_accuse` win), Detetive morre
  - **Olhar (Look)**
  - **Chat**
- **Cooldown de investigação:** 12 segundos
- **Poderes:** Perde poder de investigar se acusar errado (na implementação atual, o jogo acaba)
- **Visão especial:** Vê barra de suspeita em cada jogador com cores (verde/laranja/vermelho)
- **Recebe:** Ranking de suspeitos, pistas ofuscadas, timeline de eventos, dicas privadas de vítimas
- **Teclas de atalho:** I (investigar), nenhuma para acusar (requer confirmação)

### 2.3 Vítima (Victim)
- **Ícone:** `JogadorMasculina.png` ou `JogadorFeminina.png` (baseado no gênero)
- **Cor temática:** Verde (`#43E97B`)
- **Ações:**
  - **Reportar (Report)** — reportar comportamento suspeito de outro jogador ao grupo todo (mensagem no chat como sistema). Aumenta a suspeita do alvo.
  - **Dica para Detetive (Hint)** — enviar dica PRIVADA ao detetive (só o detetive vê). Pode escolher de lista ou escrever texto livre (max 200 chars).
  - **Olhar (Look)**
  - **Chat**
- **Após morrer:** Vira espectador. Não pode usar chat, não pode agir. Fica com opacidade reduzida e ícone 💀.

### 2.4 Gênero
- Cada jogador escolhe "Masculino" ou "Feminino" ao criar/entrar na sala
- Afeta apenas o ícone visual (não afeta gameplay)
- Bots de IA recebem gênero aleatório

---

## 3. FLUXO DO JOGO

### 3.1 Tela Inicial (Index)
- **Criar Sala:** Nome do jogador, gênero (M/F), quantidade de jogadores (3-12)
- **Entrar na Sala:** Nome do jogador, gênero, código da sala (6 caracteres alfanuméricos uppercase)
- **Seletor de idioma:** PT 🇧🇷 / EN 🇺🇸
- **Seção "Como Jogar"** expansível

### 3.2 Lobby
- Mostra grid de jogadores com avatares coloridos e ícones de gênero
- **Código da sala** visível com botão de copiar
- **Criador da sala** tem badge ⭐ e pode:
  - "Completar com IA" → preenche vagas vazias com bots
  - "Remover IA" → botão ✕ vermelho em cada bot para removê-lo
  - "Iniciar Jogo" → habilitado quando há ≥ 3 jogadores
- Jogadores que não são criador veem animação de "Aguardando..."
- **Entrada durante jogo:** Se alguém tenta entrar numa sala com jogo em andamento, substitui um bot IA (herda papel, status e cor do bot)

### 3.3 Jogo (Playing)
#### Layout
- **Header:** Código da sala | Rodada N | Papel do jogador (com ícone) | Vivos X/Y | Medidor de tensão | Botão sair ✕
- **Área central:** Círculo de jogadores (grid flexível, wrap)
- **Footer:** Barra de ações (botões variam por papel)
- **Chat fixo:** Canto inferior direito, toggle 💬 com badge de não-lidas
- **Log de eventos:** Canto inferior esquerdo, semi-transparente, últimos 15 eventos

#### Jogadores no Círculo
- Cada jogador = card clicável com avatar circular colorido, ícone PNG, nome
- Jogador morto = opacidade 0.35, não clicável, ícone 💀
- Jogador selecionado = borda ciano com glow
- Jogador próprio = borda roxa
- Bots = badge 🤖 após o nome
- Detetive vê barra de suspeita abaixo de cada jogador vivo

#### Fluxo de Ações
1. Jogador clica em outro jogador (seleciona alvo)
2. Botões de ação se habilitam
3. Executa ação → feedback visual (toast central) + som
4. Estado atualiza via WebSocket para todos

### 3.4 Fim de Jogo (Finished)
- Overlay fullscreen com blur
- Revela TODOS os papéis e ícones de cada jogador
- Título e mensagem dinâmicos conforme tipo de vitória
- **Botão "Jogar Novamente"** — visível apenas para o criador da sala
- **Botão "Sair" 🚪** — visível para todos
- **Mensagem "Aguardando anfitrião..."** — visível para não-criadores

---

## 4. CONDIÇÕES DE VITÓRIA

| Código | Vencedor | Condição | Mensagem PT | Mensagem EN |
|--------|----------|----------|-------------|-------------|
| `detective` | Detetive | Acusou o assassino corretamente | "O Detetive {nome} prendeu o Assassino: {nome}." | "Detective {name} arrested the Assassin: {name}." |
| `detective_auto` | Detetive | Assassino tentou matar o detetive | "O Detetive {nome} venceu, pois o Assassino tentou matá-lo." | "Detective {name} won because the Assassin tried to kill them." |
| `assassin` | Assassino | Todas as vítimas estão mortas | "O Assassino {nome} matou todas as vítimas." | "Assassin {name} eliminated all victims." |
| `assassin_accuse` | Assassino | Detetive acusou pessoa errada | "O Detetive {nome} acusou a pessoa errada. O Assassino era {nome}." | "Detective {name} accused the wrong person. The Assassin was {name}." |

**REGRA IMPORTANTE:** Quando TODAS as vítimas morrem, o assassino vence imediatamente — mesmo que o detetive ainda esteja vivo.

---

## 5. SISTEMA DE KILL (PISCADA DIGITAL)

### Mecânica
1. Assassino seleciona alvo e clica "Eliminar"
2. Servidor agenda morte com delay aleatório: **2 a 8 segundos**
3. Durante o delay, servidor gera **2-4 eventos de ruído** (looks falsos, atividade falsa) com timestamps ligeiramente futuros (0.1-1.5s)
4. Após delay, vítima morre → broadcast para todos
5. **15% de chance** de blackout após cada morte (tela escura por 8s, logs confusos)

### Eventos de Ruído (Camuflagem)
- `noise_look` — "alguém olhou para alguém" (falso)
- `noise_activity` — "atividade incomum" (falso)
- Mensagens aleatórias: "movimento detectado", "olhar suspeito", "atividade incomum", "interação registrada", "comportamento analisado", "sinal captado"
- Esses eventos são marcados como `is_noise: true` e aparecem misturados com eventos reais

### Blackout
- **Duração:** 8 segundos
- **Chance:** 15% após cada kill executada
- **Visual:** Overlay escuro com pulsação e texto "⚡ APAGÃO!" / "⚡ BLACKOUT!"
- **Efeito:** Logs ficam confusos durante o período
- **Som:** Tom grave prolongado

### Interferência
- **Chance:** 10% (verificada separadamente)
- **Efeito:** Dados falsos aumentam temporariamente

---

## 6. SISTEMA DE SUSPEITA (PSA — Percepção Social Artificial)

### Perfil de Suspeita por Jogador
Cada jogador tem 4 scores que compõem o total:

| Score | Peso | Gatilho | Incremento |
|-------|------|---------|------------|
| `base_score` | 10% | Ser reportado por vítima | +0.1 |
| `temporal_score` | 40% | Ação recente próxima a uma morte | +0.3 por morte |
| `activity_score` | 25% | Frequência de ações | `look`: +0.05, `interact`: +0.1, `reported`: +0.15 |
| `look_pattern_score` | 25% | Olhar para alguém que morreu logo depois | +0.35 |

**Total:** `base*0.1 + temporal*0.4 + activity*0.25 + look_pattern*0.25` (clamped 0.0-1.0)

### Decay (Desvanecimento)
- `temporal_score` decai a taxa de 0.05/segundo
- `activity_score` decai a taxa de 0.025/segundo
- `look_pattern_score` decai a taxa de 0.015/segundo

### Níveis de Suspeita
| Score | Nível | Cor |
|-------|-------|-----|
| ≥ 0.7 | `high` (Alta probabilidade) | Vermelho |
| ≥ 0.4 | `moderate` (Comportamento suspeito) | Laranja |
| ≥ 0.15 | `low` (Atividade suspeita) | Verde |
| < 0.15 | `none` (Sem evidências) | Cinza |

### Evidência Ofuscada (para Detetive)
Quando o detetive investiga, ele NUNCA recebe resposta definitiva. Recebe:
- Nível de suspeita (high/moderate/low/none)
- Score numérico
- Dicas textuais: "Atividade próxima a mortes recentes", "Frequência de ações acima do normal", "Padrão de olhar suspeito", ou "Sem evidências significativas"
- Timeline: últimos 5 eventos do suspeito nos últimos 15 segundos
- Contagem de atividade recente
- Eventos de ruído podem vazar (30% de chance de aparecer na timeline)

---

## 7. SISTEMA "OLHAR" (LOOK)

- Qualquer jogador vivo pode "olhar" para outro jogador vivo
- Gera evento `look` na timeline
- **Broadcast:** Todos veem animação "👁️ {nome}" no avatar do alvo (desaparece em 2s)
- **Log de evento:** Aparece no log lateral para todos (exceto o próprio ator)
- **Impacto na suspeita:** +0.05 de `activity_score` para quem olhou
- **Padrão de olhar:** Se alguém olhou para um jogador que morreu logo depois → +0.35 de `look_pattern_score` (MUITO suspeito)

---

## 8. SISTEMA DE CHAT

### Regras
- Mensagens limitadas a 200 caracteres
- Caracteres `<` e `>` removidos (anti-XSS)
- **Jogadores mortos NÃO podem enviar mensagens** (input desabilitado, placeholder "Espectadores não podem falar")
- Cada mensagem mostra: ícone do jogador + nome colorido + texto
- **Persistência:** Histórico salvo em `sessionStorage` por sala, restaurado ao reconectar
- **Chat limpa** quando inicia nova rodada (play again)
- Badge de não-lidas quando chat está fechado

### Mensagens Especiais do Sistema
- **Reports:** `🚨 REPORTE: {reporter} → {target}: "{reason}"` (cor verde)
- **Dicas:** `💡 DICA ({from}): {hint} sobre {target}` (cor ciano, SOMENTE para detetive)

---

## 9. SISTEMA DE VÍTIMAS

### Reportar Comportamento Suspeito
- Selecionar jogador → Botão "🚨 Reportar"
- Abre modal com opções predefinidas:
  - PT: "Está agindo de forma suspeita", "Estava olhando muito para alguém", "Evita contato visual", "Comportamento estranho após uma morte", "Parece nervoso(a)"
  - EN: "Acting suspiciously", "Staring at someone a lot", "Avoiding eye contact", "Strange behavior after a death", "Seems nervous"
- Report é broadcast para TODOS (aparece no chat como mensagem do sistema)
- Aumenta `activity_score` (+0.15) e `base_score` (+0.1) do alvo

### Dica Privada para Detetive
- Selecionar jogador → Botão "💡 Dica p/ Detetive"
- Abre modal com opções predefinidas + campo de texto livre:
  - PT: "Acho que essa pessoa é o assassino", "Essa pessoa está agindo de forma estranha", "Essa pessoa evita contato visual", "Vi algo suspeito sobre essa pessoa", "Fique de olho nessa pessoa"
  - EN: "I think this person is the assassin", "This person is acting strangely", "This person avoids eye contact", "I saw something suspicious about them", "Keep an eye on this person"
- Dica é enviada SOMENTE para o detetive (privada)
- Detetive vê no chat + toast de notificação

---

## 10. INTELIGÊNCIA ARTIFICIAL (BOTS)

### Personalidades (4 tipos, aleatório)
| Personalidade | Kill Target | Comportamento |
|---|---|---|
| `Aggressive` | Alvo aleatório | Mata rápido |
| `Cautious` | Aleatório, mas com 50% de chance de NÃO matar | Mata devagar |
| `Erratic` | Aleatório | Imprevisível |
| `Calculated` | Evita matar quem olhou recentemente (limpa rastros) | Estratégico |

### Comportamento por Papel
#### Assassino IA
1. Loop contínuo com delay aleatório (1.5-5s entre pensamentos)
2. 60% de chance de olhar para alguém (blefe)
3. Mata quando `time_since_last_kill ≥ threshold` (8-18 segundos)
4. Após matar, olha para jogador diferente do alvo (diversão de atenção)
5. **Nunca tenta matar o detetive** (filtrado automaticamente)

#### Detetive IA
1. Olha para jogadores aleatórios (50% de chance por ciclo)
2. Investiga o jogador mais suspeito quando `time_since_last ≥ threshold` (10-20s)
3. Se evidência = "high" E já investigou ≥2 vezes → 60% de chance de acusar
4. Se perdeu poder, apenas olha

#### Vítima IA
1. 40% de chance de olhar para alguém aleatório por ciclo
2. Cria ruído social

### Nomes de IA
`Shadow, Phantom, Cipher, Echo, Specter, Raven, Onyx, Viper, Storm, Ghost, Nyx, Blade, Ember, Frost, Nebula`

### Substituição Automática
- Jogador desconecta → **8 segundos de graça** para reconectar
- Se não reconectar → IA assume com mesmo papel, status, nome + "(Bot)"
- Jogador clica "Sair" → IA assume imediatamente (sem período de graça)
- Jogador novo pode entrar e substituir um bot (herda papel/status/cor)

---

## 11. SISTEMA DE ÁUDIO

Todos os sons são gerados proceduralmente via Web Audio API (nenhum arquivo externo):

| Evento | Tipo de Onda | Frequência(s) Hz | Duração | Volume |
|--------|-------------|------------------|---------|--------|
| `death` | sawtooth | 200 → 120 | 0.8s + 1.2s | 0.12/0.08 |
| `kill` | square | 800 → 400 | 0.15s + 0.3s | 0.08/0.05 |
| `investigate` | sine | 600 → 900 | 0.2s + 0.3s | 0.08/0.06 |
| `accuse` | sawtooth | 500 → 700 → 1000 | 0.15 ea | 0.1/0.08 |
| `success` | sine | 523 → 659 → 784 | 0.2 ea | 0.1 |
| `error` | square | 300 → 200 | 0.3s + 0.5s | 0.08/0.06 |
| `look` | sine | 1200 | 0.08s | 0.04 |
| `chat` | sine | 1000 | 0.05s | 0.03 |
| `blackout` | sawtooth | 80 → 60 | 2.0s + 1.5s | 0.15/0.1 |
| `tension` | sine | 100 | 3.0s | 0.03 |
| `gameOver` | sine | 400→350→300→200 | 0.3→1.0s | 0.12→0.06 |
| `victory` | sine | 523→659→784→1047 | 0.3s ea, 150ms apart | 0.1 |

---

## 12. EFEITOS VISUAIS

### Tensão
- Overlay vermelho radial que aumenta conforme jogadores morrem
- `tensão = (mortos/total) * 0.6 + (tempo_decorrido/120s) * 0.4` (clamped 0-1)
- Alpha do overlay = tensão × 0.3
- Som de tensão quando nível > 0.7 (5% de chance por tick)

### Blackout
- Overlay preto com 85% opacidade
- Animação de pulsação (opacidade 0.7 ↔ 0.95)
- Texto vermelho "⚡ APAGÃO!" com text-shadow glow

### Look Indicator
- Texto "👁️ {actor_name}" aparece sobre o avatar do alvo
- Animação pop (scale 0→1.3→1)
- Desaparece em 2 segundos

### Morte de Jogador
- Node vira opacidade 0.35
- Ícone 💀 aparece
- Avatar recebe overlay 💀
- Ponteiro desabilitado

### Tema
- Dark theme baseado em `#0a0a1a` (background)
- Acentos neon: Roxo `#6C63FF`, Rosa `#FF6584`, Verde `#43E97B`, Laranja `#F7971E`, Ciano `#00C9FF`, Vermelho `#FF4444`
- Fontes: Inter (UI) + Fira Code (monospace/codes)
- Efeito glitch no título
- Botões com glow (pseudo-element ::after com blur)
- 12 cores de avatar: `#6C63FF, #FF6584, #43E97B, #F7971E, #00C9FF, #FC5C7D, #A18CD1, #FBC2EB, #F093FB, #4FACFE, #0BA360, #FFD54F`

---

## 13. SISTEMA DE SALAS

### Criação
- Gera código aleatório de 6 caracteres hexadecimais uppercase
- Armazena em memória (não há banco de dados)

### Entrada
- Código não existe → erro "Sala não encontrada"
- Sala cheia → erro "Sala cheia"
- Jogo já começou e tem bot → substitui bot por humano
- Jogo já começou sem bots → erro "Jogo já iniciado"

### Nomes de Jogadores
- Máximo 20 caracteres
- Remove caracteres `< > & " '`
- Se vazio, usa "Jogador"

---

## 14. COMUNICAÇÃO EM TEMPO REAL

### WebSocket
- Endpoint: `/ws/{room_code}/{player_id}`
- Ping/pong a cada 25 segundos para manter vivo
- Reconexão automática a cada 2 segundos se desconectar
- Código 4001 = jogador não encontrado na sala (redirecionar para home)

### Tipos de Mensagem (Client → Server)

| Tipo | Payload | Papel |
|------|---------|-------|
| `start_game` | — | Criador no lobby |
| `fill_ai` | — | Criador no lobby |
| `kick_ai` | `{target_id}` | Criador no lobby |
| `kill` | `{target_id}` | Assassino |
| `investigate` | `{target_id}` | Detetive |
| `accuse` | `{target_id}` | Detetive |
| `look` | `{target_id}` | Todos (vivos) |
| `chat` | `{message}` | Todos (vivos) |
| `victim_report` | `{target_id, reason}` | Vítima |
| `victim_hint` | `{target_id, hint}` | Vítima |
| `play_again` | — | Criador (fim de jogo) |
| `leave_game` | — | Todos |
| `ping` | — | Todos |

### Tipos de Mensagem (Server → Client)

| Tipo | Conteúdo |
|------|----------|
| `state_update` | Estado completo personalizado por jogador |
| `lobby_update` | Estado do lobby |
| `game_started` | Redirect URL para tela de jogo |
| `game_restarted` | Signal para limpar estado e recarregar |
| `kill_result` | Resultado da tentativa de kill |
| `investigate_result` | Evidências ofuscadas |
| `accusation` | Resultado da acusação (broadcast) |
| `look_event` | Quem olhou para quem |
| `chat_message` | Mensagem de chat |
| `victim_report_broadcast` | Reporte de vítima (broadcast) |
| `victim_hint` | Dica privada (só detetive recebe) |
| `hint_sent` | Confirmação para vítima |
| `accuse_error` | Erro na acusação |
| `ai_action` | Ação de IA (look) |
| `player_replaced` | Jogador substituído por IA |
| `pong` | Resposta ao ping |

### Estado do Jogo por Jogador
Cada jogador recebe estado personalizado:
- **Seu papel revelado** (private)
- **Outros jogadores:** dados públicos (sem papel) — exceto detetive que vê scores de suspeita
- **Fim de jogo:** TODOS os papéis e ícones revelados
- **Ícones:** Durante jogo, outros jogadores sempre mostram ícone de gênero (nunca ícone de papel). Somente o próprio jogador vê seu ícone de papel.

---

## 15. ATALHOS DE TECLADO

| Tecla | Ação |
|-------|------|
| K | Eliminar (assassino) |
| I | Investigar (detetive) |
| L | Olhar |
| C | Toggle chat |
| Escape | Deselecionar alvo, fechar painéis |
| Enter | Enviar mensagem (quando input de chat focado) |

---

## 16. CONFIGURAÇÕES NUMÉRICAS


MIN_PLAYERS = 3
MAX_PLAYERS = 12
DEFAULT_PLAYERS = 6
KILL_DELAY_MIN = 2 (segundos)
KILL_DELAY_MAX = 8 (segundos)
ASSASSIN_COOLDOWN = 10 (segundos)
DETECTIVE_COOLDOWN = 12 (segundos)
ROUND_DURATION = 120 (segundos, para cálculo de tensão)
INVESTIGATION_WINDOW = 15 (segundos de logs visíveis)
SUSPICION_DECAY = 0.05 (por segundo)
BLACKOUT_DURATION = 8 (segundos)
BLACKOUT_CHANCE = 0.15 (15%)
INTERFERENCE_CHANCE = 0.10 (10%)
AI_THINK_DELAY = 1.5 - 5.0 (segundos)
AI_KILL_INTERVAL = 8 - 18 (segundos)
AI_INVESTIGATE_INTERVAL = 10 - 20 (segundos)
AI_LOOK_INTERVAL = 3 - 8 (segundos)
RECONNECT_GRACE = 8 (segundos antes de substituir por IA)


---

## 17. ASSETS VISUAIS

### Imagens PNG (4 ícones)
| Arquivo | Uso |
|---------|-----|
| `Assassino.png` | Ícone do assassino (visível apenas para o próprio + fim de jogo) |
| `Detetive.png` | Ícone do detetive (visível apenas para o próprio + fim de jogo) |
| `JogadorMasculina.png` | Ícone público masculino (vítimas, vista pública de todos) |
| `JogadorFeminina.png` | Ícone público feminino (vítimas, vista pública de todos) |

> Estes PNGs precisam ser incluídos como resources na app MAUI.

---

## 18. TRADUÇÕES COMPLETAS

### Português (PT)
```json
{
    "game_title": "Assassino da Piscada",
    "create_room": "Criar Sala",
    "join_room": "Entrar na Sala",
    "your_name": "Seu Nome",
    "room_code": "Código da Sala",
    "players": "Jogadores",
    "start_game": "Iniciar Jogo",
    "waiting": "Aguardando jogadores...",
    "you_are": "Você é",
    "assassin": "Assassino",
    "detective": "Detetive",
    "victim": "Vítima",
    "dead": "Morto",
    "alive": "Vivo",
    "spectator": "Espectador",
    "kill": "Eliminar",
    "investigate": "Investigar",
    "accuse": "Acusar",
    "look_at": "Olhar para",
    "chat": "Chat",
    "send": "Enviar",
    "died": "morreu!",
    "arrested": "Preso em nome da lei!",
    "assassin_wins": "O Assassino venceu!",
    "detective_wins": "O Detetive venceu!",
    "wrong_accusation": "Acusação errada!",
    "cooldown_active": "Aguarde o cooldown...",
    "suspicious_activity": "Atividade suspeita detectada",
    "no_evidence": "Sem evidências claras",
    "high_suspicion": "Alta probabilidade",
    "moderate_suspicion": "Comportamento suspeito",
    "blackout": "⚡ APAGÃO!",
    "interference": "📡 Interferência nos dados!",
    "game_over": "Fim de Jogo",
    "play_again": "Jogar Novamente",
    "ai_player": "Bot",
    "room_full": "Sala cheia",
    "copied": "Copiado!",
    "round": "Rodada",
    "time_left": "Tempo restante",
    "players_alive": "Jogadores vivos",
    "tension_rising": "A tensão aumenta...",
    "someone_died": "Alguém morreu...",
    "look_registered": "Olhar registrado",
    "power_lost": "Você perdeu seus poderes!",
    "fill_with_ai": "Completar com IA"
}

{
    "game_title": "Blink Assassin",
    "create_room": "Create Room",
    "join_room": "Join Room",
    "your_name": "Your Name",
    "room_code": "Room Code",
    "players": "Players",
    "start_game": "Start Game",
    "waiting": "Waiting for players...",
    "you_are": "You are",
    "assassin": "Assassin",
    "detective": "Detective",
    "victim": "Victim",
    "dead": "Dead",
    "alive": "Alive",
    "spectator": "Spectator",
    "kill": "Eliminate",
    "investigate": "Investigate",
    "accuse": "Accuse",
    "look_at": "Look at",
    "chat": "Chat",
    "send": "Send",
    "died": "died!",
    "arrested": "Arrested in the name of the law!",
    "assassin_wins": "The Assassin wins!",
    "detective_wins": "The Detective wins!",
    "wrong_accusation": "Wrong accusation!",
    "cooldown_active": "Cooldown active...",
    "suspicious_activity": "Suspicious activity detected",
    "no_evidence": "No clear evidence",
    "high_suspicion": "High probability",
    "moderate_suspicion": "Suspicious behavior",
    "blackout": "⚡ BLACKOUT!",
    "interference": "📡 Data interference!",
    "game_over": "Game Over",
    "play_again": "Play Again",
    "ai_player": "Bot",
    "room_full": "Room full",
    "copied": "Copied!",
    "round": "Round",
    "time_left": "Time left",
    "players_alive": "Players alive",
    "tension_rising": "Tension is rising...",
    "someone_died": "Someone died...",
    "look_registered": "Look registered",
    "power_lost": "You lost your powers!",
    "fill_with_ai": "Fill with AI"
}

19. ARQUITETURA SUGERIDA PARA .NET MAUI
Modelo Client-Server
A aplicação original é client-server com um servidor Python. Para MAUI, há duas opções:

Opção A: Servidor Embutido (Recomendada para APK)
O celular que cria a sala roda um servidor WebSocket embutido (ex: usando System.Net.WebSockets.WebSocketListener ou Kestrel mínimo)
Outros jogadores conectam via IP da rede local
Toda a lógica do engine roda no dispositivo host
Opção B: Servidor Externo
Manter um servidor backend (ASP.NET Core com WebSocket) hospedado
App MAUI é apenas o cliente
Mais apropriado se quiser matchmaking global
Estrutura Sugerida do Projeto MAUI

DAGroup.MAUI/
├── App.xaml / App.xaml.cs
├── MauiProgram.cs
├── Models/
│   ├── Player.cs
│   ├── GameRoom.cs
│   ├── PendingKill.cs
│   ├── GameEvent.cs
│   └── SuspicionProfile.cs
├── Services/
│   ├── GameEngine.cs          (motor do jogo — toda lógica)
│   ├── SuspicionEngine.cs     (sistema PSA)
│   ├── NoiseGenerator.cs      (camuflagem)
│   ├── AIBotService.cs        (bots com personalidades)
│   ├── WebSocketService.cs    (comunicação)
│   ├── AudioService.cs        (sons procedurais)
│   └── TranslationService.cs  (i18n PT/EN)
├── ViewModels/
│   ├── IndexViewModel.cs
│   ├── LobbyViewModel.cs
│   └── GameViewModel.cs
├── Views/
│   ├── IndexPage.xaml         (criar/entrar sala)
│   ├── LobbyPage.xaml         (aguardar jogadores)
│   └── GamePage.xaml          (tela do jogo)
├── Resources/
│   ├── Images/
│   │   ├── assassino.png
│   │   ├── detetive.png
│   │   ├── jogador_masculina.png
│   │   └── jogador_feminina.png
│   └── Fonts/
│       └── Inter-*.ttf
└── Enums/
    ├── RoleType.cs            (Assassin, Detective, Victim)
    ├── PlayerStatus.cs        (Alive, Dead, Spectator)
    ├── GamePhase.cs           (Lobby, Playing, Finished)
    └── AIPersonality.cs       (Aggressive, Cautious, Erratic, Calculated)


20. REGRAS DE NEGÓCIO CRÍTICAS (CHECKLIST)
 Assassino NUNCA pode matar o detetive (se tentar → detetive vence automaticamente)
 Acusação errada do detetive → jogo encerra imediatamente com vitória do assassino
 Todas as vítimas mortas → assassino vence (detetive vivo é irrelevante)
 Kill tem delay aleatório 2-8 segundos + eventos de ruído
 Detetive nunca recebe evidência 100% clara (sempre ofuscada)
 Mortos não podem usar chat
 Reports de vítimas são públicos, dicas são privadas (só detetive)
 Reconexão em 8 segundos mantém o jogador; após 8s, IA substitui
 Saída voluntária → IA substitui imediatamente
 Chat persiste durante a sessão, limpa ao iniciar nova rodada
 Ícones de papel são privados (outros jogadores veem ícone de gênero)
 Fim de jogo revela todos os papéis e ícones verdadeiros
 Código de sala: 6 chars alfanuméricos uppercase
 Nome: max 20 chars, sem < > & "" '
 Mensagens: max 200 chars, sem < >
 Mínimo 3 jogadores para iniciar
 Somente criador pode iniciar jogo, completar com IA, jogar novamente
 Botão sair pede confirmação
 Bots IA têm nomes e gêneros aleatórios
 Novo jogador entrando durante jogo substitui um bot (herda papel/status)

 21. SEGURANÇA
Toda validação de ação no servidor (anti-cheat)
Papéis nunca expostos a outros jogadores até fim de jogo
Input sanitizado (remove HTML tags)
Kill events visíveis apenas para o assassino na timeline
Investigação visível apenas para o detetive na timeline
WebSocket autenticado por player_id (UUID gerado no servidor)
Sem persistência em disco (tudo em memória)
22. FLUXO COMPLETO DE UMA PARTIDA
Jogador A cria sala com 6 vagas → recebe código ABC123
Jogadores B, C entram pelo código → aparecem no lobby
A clica "Completar com IA" → 3 bots preenchem as 3 vagas restantes
A clica "Iniciar Jogo" → servidor sorteia papéis aleatoriamente
Todos recebem estado com seu papel privado → tela de jogo
Assassino (ex: Bot Shadow) começa a agir: olha para jogadores, espera 8-18s, mata vítimaAssassino
Kill agendada com delay 3.5s + 3 eventos de ruído gerados
Vítima morre → broadcast → 💀 aparece → log "Alguém morreu..."
15% chance de blackout: tela escurece por 8s
Detetive investiga suspeito → recebe "Comportamento suspeito" + timeline parcial
Vítima C reporta: "Está agindo de forma suspeita" sobre Bot Shadow → aparece no chat
Vítima B envia dica privada ao detetive: "Acho que essa pessoa é o assassino" sobre Shadow
Detetive acusa Shadow → CORRETO → Detetive vence! → Overlay de fim de jogo
Todos os papéis revelados com ícones reais
Criador clica "Jogar Novamente" → papéis são redistribuídos → nova rodada


Copie este conteúdo e salve como `MAUI_DAG.md` na raiz do projeto (`c:\Python\DAGroup\MAUI_DAG.md`). O documento cobre toda a lógica, regras, configurações, comunicação, IA, áudio, visual e traduções — tudo o que outro agent precisa para recriar a aplicação em .NET MAUI.


## --------------------------------------------------------------------------------------------- ##

## dotnet workload install maui-android

Por que maui-android e não maui?

maui instala SDK para todas as plataformas (Android, iOS, Mac, Windows, Tizen) — muito mais pesado e você não precisa de iOS/Mac no Windows.
maui-android instala apenas o necessário para Android — é mais leve e suficiente para compilar e gerar o APK.
Depois de instalar, o fluxo para gerar o APK é:

# Criar o projeto
dotnet new maui -n DAGroup.MAUI

# Compilar APK (debug)
dotnet build -f net9.0-android

# Gerar APK assinado (release)
dotnet publish -f net9.0-android -c Release



The user wants me to create a comprehensive MD file called "MAUI_DAG.md" that describes all the logic, functionality, and rules of the application so that another LLM agent (Claude Opus 4.6) can use it to create a MAUI Android application. They also want me to reference the README.md file.

Let me first check if MAUI_DAG.md already exists (from the conversation summary, it was created before), and then read through all the current source files to create an up-to-date comprehensive specification document.

Let me start by reading all the key source files to understand the current state of the application.
Created 2 todos
Read roles.py
Read engine.py, lines 1 to 300
Read suspicion.py
Read config.py
Read events.py
Read engine.py, lines 300 to 568
Read ai.py
Read manager.py
Read game.py, lines 1 to 350
Read lobby.py
Read main.py
Read requirements.txt
Read game.py, lines 290 to 400
Read game.js, lines 1 to 600
Read game.js, lines 600 to 967
Read sounds.js
Now let me read the HTML templates and CSS:
Now let me read the remaining CSS and check for the images:
Now let me read the remaining part of the CSS and the run.py:
Now I have read the entire codebase. Let me also check if there's already a MAUI_DAG.md file:
There's a MAUI_DAG_L.md but the user wants a new MAUI_DAG.md. Let me create it now with the comprehensive specification.

Now let me read the HTML templates and CSS:

Now let me read the remaining CSS and check for the images:

Now let me read the remaining part of the CSS and the run.py:

Now I have read the entire codebase. Let me also check if there's already a MAUI_DAG.md file:

There's a MAUI_DAG_L.md but the user wants a new MAUI_DAG.md. Let me create it now with the comprehensive specification.

Starting: Create comprehensive MAUI_DAG.md (2/2)

Created MAUI_DAG.md

Compacted conversation

MAUI_DAG.md criado com sucesso — 21 seções, ~900 linhas cobrindo:

Regras completas do jogo (papéis, condições de vitória, mecânicas)
Configurações (40+ constantes com valores exatos)
Motor do jogo (kill com delay, investigação ofuscada, acusação, look)
PSA (4 camadas de suspeita com pesos e decaimento)
IA (4 personalidades, comportamento por papel, 15 nomes)
Protocolo WebSocket (13+ tipos de mensagem, payloads, grace period)
Interface (renderização, chat, modais, atalhos, cooldowns)
Áudio (12 sons procedurais com frequências e waveforms)
Design visual (cores, efeitos, responsividade)
Traduções PT/EN (40+ chaves)
Arquitetura MAUI sugerida (MVVM, estrutura de pastas, stack, permissões Android)
Checklist de implementação em 3 fases (MVP → Completo → Polish)
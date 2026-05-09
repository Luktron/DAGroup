# Deploy no Vercel (GitHub)

Este projeto foi adaptado para rodar no Vercel com FastAPI + templates.

## O que ja esta configurado

- Entrypoint serverless: api/index.py
- Roteamento global para o backend Python: vercel.json
- Inclusao de templates, static e imagens no bundle da function: vercel.json
- Paths absolutos para static/templates no backend (compatibilidade com ambiente serverless)

## Como publicar

1. Suba o codigo para o GitHub.
2. No painel do Vercel, clique em New Project.
3. Importe o repositorio.
4. Framework Preset: Other.
5. Build Command: deixe vazio.
6. Output Directory: deixe vazio.
7. Deploy.

## Observacao importante sobre WebSocket

A aplicacao usa WebSocket e estado em memoria para o jogo em tempo real.
Em ambiente serverless, conexoes longas e estado local podem nao ser estaveis entre execucoes.

Para producao com multiplayer em tempo real, o ideal e mover:

- Estado de salas/jogadores para Redis ou banco externo.
- Canal realtime para um servico dedicado (ex.: Ably, Pusher, Supabase Realtime) ou backend com conexao persistente.

Com a configuracao atual, o deploy no Vercel fica pronto para paginas/templates e endpoints HTTP.

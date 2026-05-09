# Deploy no Vercel

## O que está configurado

- Entrypoint serverless: `api/index.py` com handler ASGI
- Roteamento global para o backend: `vercel.json`
- Inclusão de templates, static e imagens no bundle
- Runtime Python: 3.11

## Como publicar (recomendado)

### Opção 1: Via Vercel Dashboard (Recomendado)

1. Suba o código para o GitHub
2. Acesse https://vercel.com/new
3. Selecione "Import Git Repository"
4. Importe seu repositório
5. Deixe as configurações padrão:
   - **Framework Preset**: Other
   - **Build Command**: (deixe vazio)
   - **Output Directory**: (deixe vazio)
6. Clique em "Deploy"

### Opção 2: Via CLI

```bash
npm install -g vercel
vercel --prod
```

## Importante: Limitações do Vercel Serverless

⚠️ **WebSocket em Vercel tem limitações:**
- Conexões de longa duração podem expirar
- Estado em memória não persiste entre requisições
- Não é recomendado para jogos em tempo real com muitos jogadores

### Para funcionar melhor no Vercel:
1. Implemente fallback para HTTP polling
2. Use um serviço externo para gerenciar estado (Redis, Supabase, Ably)
3. Considere usar Railway ou Render para multiplayer em tempo real

## Se não funcionar

### Erro: "Cannot find module"
- Verifique se `requirements.txt` está na raiz do projeto
- Confirme que `api/index.py` existe e importa `app.main`

### Erro: "Connection timeout"
- WebSocket pode estar enfrentando problemas
- Use HTTP endpoints em vez de WebSocket no Vercel
- Considere migrar para Railway para melhor suporte a WebSocket

### Erro: "Static files not found"
- Vercel incluiu automaticamente os arquivos de `app/` via `vercel.json`
- Caminhos absolutos em `app/main.py` estão configurados corretamente

## Exemplo de URL do Vercel

Após deploy bem-sucedido:
- URL: `https://seu-projeto.vercel.app`
- API: `https://seu-projeto.vercel.app/api/...`


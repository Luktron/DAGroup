# Deploy no Railway

## O que está configurado

- Comando de start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Dependências em: `requirements.txt` e `Procfile`

## Como publicar

1. Suba o código para o GitHub
2. No painel do Railway:
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Selecione o repositório
3. Railway detectará automaticamente o `Procfile` e instalará as dependências
4. A aplicação iniciará em `http://your-railway-url.up.railway.app`

## Notas importantes

- Railway usa a variável `$PORT` (sem valor padrão)
- WebSocket funciona normalmente no Railway
- Estado em memória é mantido durante a sessão do dyno
- Para múltiplas instâncias, use Redis para compartilhar estado

## Se não iniciar

1. Verifique os logs: Railway > Logs
2. Certifique-se de que `requirements.txt` está atualizado
3. Confirme que Python 3.10+ está selecionado

# Guia de Troubleshooting - Deploy

## Checklist antes de fazer deploy

- [ ] `requirements.txt` está na pasta raiz com todas as dependências
- [ ] `api/index.py` existe e importa a app corretamente
- [ ] `app/main.py` existe e cria a instância FastAPI
- [ ] Pasta `app/` contém todas as rotas, templates e static files
- [ ] Nenhum erro local ao executar `python run.py`

## Erros comuns no Railway

### Erro: Port already in use
**Causa**: Variável de porta incorreta
**Solução**: Verifique `Procfile` e `railway.json` - devem usar `$PORT`
```bash
# Correto
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Incorreto ❌
web: uvicorn app.main:app --host 0.0.0.0 --port 5052
```

### Erro: ModuleNotFoundError
**Causa**: Dependência faltando
**Solução**: Atualize `requirements.txt`:
```bash
pip freeze > requirements.txt
```

### Erro: Static files not found (404)
**Verificar**:
1. Pasta `app/static/` existe com arquivos
2. Pasta `app/images/` existe com imagens
3. No `app/main.py`:
```python
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/images", StaticFiles(directory=str(BASE_DIR / "images")), name="images")
```

## Erros comuns no Vercel

### Erro: Function runtime error
**Causa**: `api/index.py` não exporta handler corretamente
**Solução**: Confirme que tem:
```python
from app.main import app
handler = app
```

### Erro: 502 Bad Gateway
**Causa**: Módulo não encontrado durante build
**Solução**:
1. Verifique se todos os imports em `app/main.py` funcionam localmente
2. Teste: `python -c "from app.main import app"`
3. Confirme `vercel.json` com `"includeFiles": ["app/**", "requirements.txt"]`

### Erro: Static files not found no Vercel
**Nota**: Vercel serverless tem limitações com arquivos estáticos
**Solução melhor**: Servir estáticos via CDN externo (Cloudflare, AWS S3) ou:
- Use Railway/Render para melhor suporte

## WebSocket não funciona após deploy

### Railway ✅ (funciona bem)
WebSocket funciona normalmente. Se não funcionar:
- Verifique se a porta está correta
- Rode `railway logs` para ver erros
- Teste com Cliente WebSocket externo

### Vercel ❌ (limitações)
Vercel Serverless não suporta bem WebSocket
**Opções**:
1. Migre para Railway/Render
2. Use HTTP polling em vez de WebSocket
3. Use serviço realtime externo (Supabase, Ably, Socket.IO)

## Como debugar

### Local (funciona?)
```bash
python run.py
# Acesse http://localhost:5052
```

### Railway
```bash
railway logs -f
# Monitore logs em tempo real
```

### Vercel
1. Dashboard > Deployments > Logs
2. Veja erros durante build e runtime

## Teste rápido

Após deploy, teste esses endpoints:

```bash
# Verificar se aplicação está rodando
curl https://seu-app.com/

# Listar rotas (se documentação está ativada)
curl https://seu-app.com/docs

# Testar WebSocket (pode falhar no Vercel)
wscat -c wss://seu-app.com/ws
```

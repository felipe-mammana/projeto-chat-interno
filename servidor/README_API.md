# API da Clinica

## 1) Instalar dependencias

```bash
pip install -r requirements-api.txt
```

## 2) Configurar ambiente

Copie `.env.example` para `.env` e ajuste os valores do banco:

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

## 3) Subir servidor

```bash
python api_server.py
```

A API sobe em `http://0.0.0.0:8000` por padrao.

## 4) Conectar app desktop nesta API

No ambiente do cliente (`main.py`), defina:

- `REMOTE_API_URL=http://IP_DO_SERVIDOR:8000`

Sem essa variavel, o app continua em modo local (acesso direto ao banco).

## Endpoints principais

- `GET /health`
- `GET /health/db`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /chat/message`
- `POST /admin/{action}`

## Exemplo login

```json
POST /auth/login
{
  "usuario": "admin",
  "senha": "123456"
}
```

## Exemplo chat

```json
POST /chat/message
{
  "token": "SEU_TOKEN",
  "mensagem": "ramal da maria"
}
```

## Exemplo admin

Para listar medicos:

```json
POST /admin/listar_medicos
{
  "token": "SEU_TOKEN_ADMIN",
  "payload": {}
}
```

Para criar medico:

```json
POST /admin/criar_medico
{
  "token": "SEU_TOKEN_ADMIN",
  "payload": {
    "nome": "Dr. Exemplo",
    "crm": "12345",
    "ativo": 1
  }
}
```

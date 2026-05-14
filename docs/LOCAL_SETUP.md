# Ambiente local (Windows)

## 1) Pré‑requisitos

- Python 3.11+
- MySQL Server local
- MySQL Client (`mysql` e `mysqldump` no PATH)

## 2) Criar virtualenv e instalar dependências

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se for usar a API local (pasta `servidor`):

```powershell
pip install -r servidor\requirements-api.txt
```

## 3) Configurar variáveis de ambiente do banco

Copie o arquivo e ajuste:

```powershell
Copy-Item .env.local.example .env.local
```

O script `scripts\run_local.ps1` lê esse arquivo e exporta as variáveis.

## 4) Rodar o app em modo local (acesso direto ao banco)

```powershell
.\scripts\run_local.ps1
```

## 5) (Opcional) Rodar a API local

```powershell
Copy-Item servidor\.env.example servidor\.env
python servidor\api_server.py
```

## 6) Puxar banco remoto para o local

Crie um arquivo `.env.dbpull` com as credenciais do banco remoto:

```
REMOTE_DB_HOST=1.2.3.4
REMOTE_DB_PORT=3306
REMOTE_DB_USER=usuario
REMOTE_DB_PASSWORD=senha
REMOTE_DB_NAME=clinica

LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=3306
LOCAL_DB_USER=root
LOCAL_DB_PASSWORD=
LOCAL_DB_NAME=clinica
```

Gerar dump:

```powershell
.\scripts\db_pull.ps1
```

Gerar dump e importar no MySQL local:

```powershell
.\scripts\db_pull.ps1 -Import
```

## Banco fake para commit publico

O projeto inclui um banco de exemplo sem dados reais em `database\fake_seed.sql`.
Para recriar a base local com dados ficticios:

```powershell
mysql -u root -p < database\fake_seed.sql
```

Login inicial do ambiente fake:

- Usuario: `admin`
- Senha: `123456`

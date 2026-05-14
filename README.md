<div align="center">
  <img src="img/logo-color.png" alt="Projeto Chat Interno" width="120" />

  <h1>Projeto Chat Interno</h1>

  <p>
    Assistente interno desktop para consultas operacionais de clínica, com chatbot, painel administrativo,
    autenticação por perfil, integração MySQL e API remota opcional.
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/MySQL-Database-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL" />
    <img src="https://img.shields.io/badge/PyWebView-Desktop-111827?style=for-the-badge" alt="PyWebView" />
    <img src="https://img.shields.io/badge/HTML5-Frontend-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
    <img src="https://img.shields.io/badge/JavaScript-UI-F7DF1E?style=for-the-badge&logo=javascript&logoColor=111827" alt="JavaScript" />
  </p>
</div>

---

## 🌑 Visão Geral

O **Projeto Chat Interno** é uma aplicação desktop corporativa para centralizar consultas internas de uma clínica. O sistema oferece um chatbot operacional para localizar médicos, funcionários, setores, agendas, ramais, e-mails, procedimentos e códigos CNN, além de um painel administrativo para manutenção dos cadastros.

A aplicação roda principalmente como **desktop app com PyWebView**, renderizando telas HTML locais e chamando métodos Python por uma ponte JavaScript. O backend pode operar em dois modos:

- **Modo local:** o desktop acessa o MySQL diretamente.
- **Modo remoto:** o desktop consome uma API FastAPI configurada por `REMOTE_API_URL`.

O objetivo real do projeto é reduzir consultas manuais recorrentes dentro da operação clínica, mantendo dados administrativos em uma base MySQL e disponibilizando uma interface leve para usuários internos.

---

## ✨ Funcionalidades

### Chat Operacional

- Busca inteligente de médicos por nome completo, nome parcial e iniciais.
- Exibição de CRM, agenda, regras médicas e requisitos por médico.
- Consulta de procedimentos realizados por médico.
- Consulta de procedimentos duplos e códigos CNN.
- Busca de funcionários por nome, ramal, e-mail e setor.
- Listagem de funcionários por setor.
- Guia de uso embutido no chat.
- Respostas em HTML renderizadas diretamente na interface desktop.
- Processamento assíncrono de mensagens via `threading.Thread` para evitar travamento visual.

### Painel Administrativo

- Dashboard administrativo com contagem de médicos e dados operacionais.
- CRUD de médicos.
- CRUD de funcionários.
- CRUD de setores.
- CRUD de procedimentos.
- CRUD de tipos de atendimento.
- CRUD de agendas médicas.
- CRUD de procedimentos duplos CNN.
- Gestão de regras médicas por profissional.
- Gestão de logins vinculados a funcionários.
- Controle de acesso ao painel por perfil `admin`.

### Desktop UX

- Janela de login.
- Widget flutuante.
- Janela de chat compacta.
- Painel administrativo em tela cheia.
- Controle de sessão local com expiração.
- Bloqueio opcional de posição da janela de chat em Windows com `win32gui`, quando disponível.

### API Remota Opcional

- Autenticação via endpoint HTTP.
- Envio de mensagens para o chatbot.
- Proxy dinâmico para métodos administrativos.
- Sessões em memória com token seguro gerado por `secrets.token_urlsafe`.
- Health check da aplicação e do banco.

---

## 🧱 Arquitetura

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Desktop Client                              │
│                                                                     │
│  login.html   chat.html   widget.html   painel_admin.html           │
│      │          │          │              │                         │
│      └──────────┴──────────┴──────────────┘                         │
│                         PyWebView JS API                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Python Application                          │
│                                                                     │
│  main.py  ── bridge desktop, sessão, janelas, admin proxy            │
│  app.py   ── regras de conversa, matching e cards HTML               │
│  auth.py  ── autenticação bcrypt                                     │
│  db.py    ── pool/conexão MySQL                                      │
│  admin_api.py ── operações administrativas CRUD                      │
│  queries.py   ── consultas de domínio                                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
               ┌────────────────┴────────────────┐
               ▼                                 ▼
┌─────────────────────────────┐     ┌──────────────────────────────┐
│       MySQL Local            │     │      FastAPI Opcional         │
│  clinica / fake_seed.sql     │     │  servidor/api_server.py       │
└─────────────────────────────┘     └──────────────┬───────────────┘
                                                    │
                                                    ▼
                                      ┌──────────────────────────────┐
                                      │          MySQL Remoto         │
                                      └──────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```text
.
├── .env.local.example
├── .gitignore
├── README.md
├── admin_api.py
├── app.py
├── auth.py
├── backend_client.py
├── chat.html
├── database/
│   └── fake_seed.sql
├── db.py
├── docs/
│   └── LOCAL_SETUP.md
├── img/
│   ├── gemini.ico
│   ├── logo-color.png
│   └── logo.png
├── login.html
├── main.py
├── nlp.py
├── painel_admin.html
├── queries.py
├── requirements.txt
├── scripts/
│   ├── db_pull.ps1
│   └── run_local.ps1
├── servidor/
│   ├── .env.example
│   ├── README_API.md
│   ├── api_server.py
│   └── requirements-api.txt
└── widget.html
```

| Caminho | Responsabilidade |
| --- | --- |
| `main.py` | Ponto de entrada desktop, criação das janelas PyWebView, sessão local, ponte JS/Python e proxy administrativo. |
| `app.py` | Motor conversacional baseado em regras, normalização de texto, busca fuzzy e geração de respostas HTML. |
| `queries.py` | Consultas MySQL reutilizadas pelo chatbot. |
| `admin_api.py` | Camada administrativa com operações CRUD e regras de manutenção de cadastros. |
| `auth.py` | Autenticação com hashes bcrypt e verificação de permissões. |
| `db.py` | Configuração de conexão e pool MySQL via variáveis de ambiente. |
| `backend_client.py` | Cliente HTTP para uso do desktop em modo remoto. |
| `servidor/api_server.py` | API FastAPI opcional para autenticação, chat e administração remota. |
| `database/fake_seed.sql` | Schema MySQL e dados fictícios para desenvolvimento seguro. |
| `scripts/run_local.ps1` | Carrega `.env.local` e inicia o app desktop. |
| `scripts/db_pull.ps1` | Gera dump remoto via `mysqldump` e pode importar localmente. |
| `*.html` | Interfaces locais do login, chat, widget e painel administrativo. |

---

## 🛠️ Tecnologias

| Categoria | Tecnologia | Uso no projeto |
| --- | --- | --- |
| Linguagem | [Python](https://www.python.org/) | Backend local, desktop bridge, autenticação, acesso a banco e API. |
| Desktop | [PyWebView](https://pywebview.flowrl.com/) | Renderização das telas HTML como aplicação desktop. |
| API | [FastAPI](https://fastapi.tiangolo.com/) | Servidor HTTP opcional para operação remota. |
| ASGI | [Uvicorn](https://www.uvicorn.org/) | Execução da API FastAPI. |
| Banco de dados | [MySQL](https://www.mysql.com/) | Persistência de médicos, funcionários, setores, agendas, logins e procedimentos. |
| Driver MySQL | [mysql-connector-python](https://dev.mysql.com/doc/connector-python/en/) | Conexão e pooling com MySQL. |
| Autenticação | [bcrypt](https://pypi.org/project/bcrypt/) | Hash e verificação de senhas. |
| NLP local | [RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/) | Similaridade textual para buscas aproximadas. |
| Configuração | [python-dotenv](https://pypi.org/project/python-dotenv/) | Leitura de `.env` na API. |
| Frontend | HTML, CSS e JavaScript | Interfaces desktop locais integradas ao PyWebView. |
| Scripts | PowerShell | Automação de execução local e dump/importação MySQL. |

### Tecnologias não detectadas

| Item | Status |
| --- | --- |
| Docker | Não há `Dockerfile` ou `docker-compose.yml` no repositório. |
| ORM | Não há SQLAlchemy/Django ORM; o acesso ao banco usa SQL direto com `mysql-connector-python`. |
| Mensageria / filas | Não há RabbitMQ, Kafka, Celery, RQ ou serviço equivalente. |
| Cache externo | Não há Redis, Memcached ou cache distribuído. |
| WebSocket | Não há implementação WebSocket. |
| IA externa | Não há integração com OpenAI, Gemini ou outro provedor de IA; o matching é local com regras e RapidFuzz. |
| Testes automatizados | Não há suíte de testes versionada. |

---

## 🚀 Como Executar

### Pré-requisitos

- Python 3.11 ou superior.
- MySQL Server local ou remoto.
- MySQL Client no `PATH` para usar `mysql` e `mysqldump`.
- Windows recomendado para a experiência desktop completa com PyWebView/Edge WebView2.

### 1. Clonar o repositório

```powershell
git clone https://github.com/felipe-mammana/projeto-chat-interno.git
cd projeto-chat-interno
```

### 2. Criar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências do app desktop

```powershell
pip install -r requirements.txt
```

### 4. Configurar banco local

```powershell
Copy-Item .env.local.example .env.local
mysql -u root -p < database\fake_seed.sql
```

Credenciais iniciais do banco fake:

| Usuário | Senha | Perfil |
| --- | --- | --- |
| `admin` | `123456` | `admin` |
| `financeiro` | `123456` | `usuario` |

### 5. Executar desktop em modo local

```powershell
.\scripts\run_local.ps1
```

O script carrega as variáveis de `.env.local` e executa:

```powershell
python main.py
```

### 6. Executar API remota opcional

```powershell
pip install -r servidor\requirements-api.txt
Copy-Item servidor\.env.example servidor\.env
python servidor\api_server.py
```

Por padrão, a API sobe em:

```text
http://0.0.0.0:8000
```

Para conectar o desktop nessa API, defina no ambiente ou em `config.json`:

```text
REMOTE_API_URL=http://127.0.0.1:8000
```

### 7. Build desktop

O repositório não versiona um script de build dedicado. Existe suporte implícito a execução empacotada em `main.py` por meio de `sys.frozen` e `_MEIPASS`, mas o arquivo `.spec` local está ignorado pelo Git.

### 8. Docker

Não há configuração Docker neste repositório. Nenhum comando Docker é necessário para o fluxo atual.

### 9. Testes

Não há framework de testes configurado. A verificação mínima atualmente aplicável é a compilação dos módulos Python:

```powershell
python -m py_compile admin_api.py app.py auth.py backend_client.py db.py main.py nlp.py queries.py servidor\api_server.py
```

---

## 🔐 Variáveis de Ambiente

### Aplicação e banco

| Variável | Descrição |
| --- | --- |
| `DB_HOST` | Host do MySQL. Padrão usado pelo código: `127.0.0.1`. |
| `DB_PORT` | Porta do MySQL. Padrão: `3306`. |
| `DB_USER` | Usuário do banco. |
| `DB_PASSWORD` | Senha do banco. |
| `DB_NAME` | Nome do banco. Padrão: `clinica`. |
| `DB_USE_POOL` | Habilita pool de conexões quando `1`. |
| `DB_POOL_NAME` | Nome opcional do pool MySQL. Padrão interno: `clinica_pool`. |
| `DB_POOL_SIZE` | Tamanho do pool MySQL. Padrão interno: `5`. |
| `REMOTE_API_URL` | URL da API remota usada pelo desktop. Quando ausente, o app usa acesso local ao MySQL. |

### API

| Variável | Descrição |
| --- | --- |
| `API_HOST` | Host de bind do Uvicorn. Exemplo em `servidor/.env.example`: `192.168.1.57`. |
| `API_PORT` | Porta da API. Padrão interno: `8000`. |
| `API_RELOAD` | Ativa reload do Uvicorn quando `1`. |
| `LOG_LEVEL` | Nível de logging da API. Exemplo: `INFO`. |

### Script de dump/importação

| Variável | Descrição |
| --- | --- |
| `REMOTE_DB_HOST` | Host do banco remoto usado por `scripts/db_pull.ps1`. |
| `REMOTE_DB_PORT` | Porta do banco remoto. Padrão do script: `3306`. |
| `REMOTE_DB_USER` | Usuário do banco remoto. |
| `REMOTE_DB_PASSWORD` | Senha do banco remoto. |
| `REMOTE_DB_NAME` | Nome do banco remoto. |
| `LOCAL_DB_HOST` | Host do banco local para importação. |
| `LOCAL_DB_PORT` | Porta do banco local. |
| `LOCAL_DB_USER` | Usuário do banco local. |
| `LOCAL_DB_PASSWORD` | Senha do banco local. |
| `LOCAL_DB_NAME` | Nome do banco local de destino. |

---

## 🌐 Endpoints da API

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/health` | Retorna status básico da API. |
| `GET` | `/health/db` | Testa conexão com o banco MySQL. |
| `POST` | `/auth/login` | Autentica usuário e cria token de sessão em memória. |
| `POST` | `/auth/logout` | Remove token de sessão. |
| `POST` | `/chat/message` | Processa uma mensagem do chatbot para uma sessão autenticada. |
| `POST` | `/admin/{action}` | Executa dinamicamente uma ação administrativa exposta por `AdminAPI`. Requer perfil `admin`. |

### Exemplos de payload

```json
{
  "usuario": "admin",
  "senha": "123456"
}
```

```json
{
  "token": "TOKEN_DA_SESSAO",
  "mensagem": "ramal da ana"
}
```

```json
{
  "token": "TOKEN_ADMIN",
  "payload": {
    "nome": "Dr. Exemplo",
    "crm": "CRM-TESTE-0001",
    "ativo": 1
  }
}
```

---

## 🗄️ Banco de Dados

O banco principal é MySQL. O schema fake versionado em `database/fake_seed.sql` cria a base `clinica` com dados fictícios e sem informações reais.

### Entidades principais

| Tabela | Finalidade |
| --- | --- |
| `setores` | Cadastro de áreas internas da clínica. |
| `funcionarios` | Cadastro de colaboradores, ramais, e-mails, status e vínculo com setor. |
| `logins` | Usuários autenticáveis, hash bcrypt, nível de acesso e vínculo com funcionário. |
| `medicos` | Cadastro de médicos, CRM e status ativo/inativo. |
| `medico_regras` | Regras clínicas por médico, incluindo IMC e observações. |
| `procedimentos` | Catálogo de procedimentos. |
| `medico_procedimento` | Relação N:N entre médicos e procedimentos. |
| `tipos_atendimento` | Tipos de atendimento disponíveis. |
| `agenda_medico` | Agenda por médico, dia da semana e horário. |
| `agenda_atendimento` | Relação entre agenda e tipos de atendimento. |
| `cnn_dupla` | Cadastro de procedimentos duplos com código CNN. |
| `cnn_dupla_procedimento` | Relação N:N entre procedimentos duplos e procedimentos. |
| `chatbot_base_setor` | Base de respostas por setor para consultas internas. |

### Views de compatibilidade

| View | Finalidade |
| --- | --- |
| `cnn_duplos` | Compatibiliza consultas legadas que esperam colunas `codigo` e `nome`. |
| `procedimento_duplo_itens` | Compatibiliza consultas legadas por `duplo_id` e `procedimento_id`. |

---

## 🧭 Fluxos Principais

### Autenticação desktop local

```text
login.html
  └── window.pywebview.api.login()
        └── main.py
              └── auth.autenticar()
                    └── MySQL logins + funcionarios
```

### Chat local

```text
chat.html
  └── enviar_mensagem_async()
        └── main.py
              └── app.responder()
                    ├── queries.py
                    ├── RapidFuzz
                    └── MySQL
```

### Modo remoto

```text
Desktop
  └── backend_client.py
        └── FastAPI /auth, /chat, /admin
              └── MySQL
```

---

## 🧪 Testes

Não há testes unitários, de integração, carga ou cobertura configurados no repositório.

Validação executável atualmente disponível:

```powershell
python -m py_compile admin_api.py app.py auth.py backend_client.py db.py main.py nlp.py queries.py servidor\api_server.py
```

Recomendações técnicas:

- Adicionar testes unitários para `auth.py`, `app.py` e `backend_client.py`.
- Adicionar testes de integração para `AdminAPI` com banco MySQL de teste.
- Adicionar testes de contrato para endpoints FastAPI.
- Adicionar fixtures SQL isoladas para cenários administrativos.

---

## 🛡️ Segurança

### Implementado

- Senhas armazenadas como hash bcrypt.
- Consultas SQL parametrizadas com placeholders `%s`.
- Separação de níveis de usuário (`usuario`, `gerente`, `admin`).
- Bloqueio do painel administrativo para usuários não-admin no desktop.
- Endpoint `/admin/{action}` exige sessão válida e nível `admin`.
- Tokens de sessão da API gerados com `secrets.token_urlsafe`.
- Arquivos `.env`, dumps, bancos locais e caches protegidos por `.gitignore`.
- Seed versionado usa dados fictícios e domínio `.test`.

### Não implementado

- Não há JWT.
- Não há refresh token.
- Não há criptografia de sessão local em arquivo.
- Não há rate limiting.
- Não há middleware CORS customizado.
- Não há auditoria persistente de ações administrativas.
- Não há gerenciamento persistente/distribuído de sessões da API; as sessões ficam em memória.

---

## 🔄 Workers, Jobs e Automações

O projeto não possui workers externos, filas, schedulers ou background jobs distribuídos.

Processamentos assíncronos detectados:

- `threading.Thread` em `main.py` para processar mensagens do chat sem bloquear a UI.
- Thread de controle de posição da janela quando o bloqueio visual está ativo.

Automações locais:

- `scripts/run_local.ps1` para carregar ambiente e iniciar o desktop.
- `scripts/db_pull.ps1` para dump remoto e importação local MySQL.

---

## 🔌 Integrações

| Integração | Tipo | Finalidade |
| --- | --- | --- |
| MySQL | Banco de dados | Persistência operacional e administrativa. |
| FastAPI opcional | HTTP API | Operação remota para desktop client. |
| PyWebView | Desktop bridge | Comunicação JavaScript ↔ Python. |
| Edge WebView2 | Runtime desktop | Backend visual usado por `web.start(gui="edgechromium")`. |
| Tailwind CDN em `login.html` | Frontend CDN | Estilização da tela de login via script externo. |

---

## 📦 Estado do Repositório

| Item | Status |
| --- | --- |
| Código Python | Presente |
| Frontend HTML/CSS/JS | Presente |
| Banco fake | Presente em `database/fake_seed.sql` |
| API HTTP | Presente em `servidor/api_server.py` |
| Docker | Não detectado |
| Testes | Não detectados |
| CI/CD | Não detectado |
| Package manager JS | Não detectado |
| ORM | Não detectado |
| Mensageria/cache | Não detectados |

---

## 🧹 Higiene e Organização

O repositório ignora artefatos e arquivos sensíveis por padrão:

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `build/`
- `dist/`
- `.env`
- `.env.*`
- `config.json`
- `session.json`
- `db_backups/`
- dumps e bancos locais

Arquivos de exemplo permitidos:

- `.env.local.example`
- `servidor/.env.example`

---

## 🗺️ Roadmap Técnico Recomendado

- Estruturar o backend em pacotes (`src/`, `services/`, `repositories`, `ui/`) para reduzir acoplamento.
- Migrar SQL bruto para uma camada de repositórios consistente.
- Adicionar testes automatizados e pipeline de CI.
- Adicionar Docker Compose para API + MySQL em desenvolvimento.
- Persistir sessões remotas em banco ou cache quando a API for usada em produção.
- Implementar auditoria administrativa.
- Substituir scripts CDN externos por assets locais, se o desktop precisar operar offline.
- Padronizar encoding UTF-8 nos arquivos HTML/Python para evitar caracteres corrompidos.

---

<div align="center">
  <sub>Projeto desktop interno para operação clínica, com MySQL, PyWebView e API FastAPI opcional.</sub>
</div>

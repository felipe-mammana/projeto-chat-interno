import inspect
import logging
import os
import secrets
import sys
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from admin_api import AdminAPI
from app import responder
from auth import autenticar
from db import test_connection

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("clinica-api")

app = FastAPI(title="Clinica API", version="1.0.0")
admin_api = AdminAPI()


@dataclass
class SessionData:
    usuario: str
    nome: str
    nivel: str
    id_setor: int | None


SESSIONS: dict[str, SessionData] = {}


class LoginRequest(BaseModel):
    usuario: str
    senha: str


class ChatRequest(BaseModel):
    token: str
    mensagem: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    token: str


class AdminCallRequest(BaseModel):
    token: str
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict[str, Any]:
    ok, message = test_connection()
    return {"ok": ok, "message": message}


@app.post("/auth/login")
def login(data: LoginRequest) -> dict[str, Any]:
    result = autenticar(data.usuario, data.senha)
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result.get("msg", "Falha no login"))

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = SessionData(
        usuario=data.usuario,
        nome=result.get("nome", "Usuario"),
        nivel=result.get("nivel", "usuario"),
        id_setor=result.get("id_setor"),
    )

    return {
        "ok": True,
        "token": token,
        "nome": SESSIONS[token].nome,
        "nivel": SESSIONS[token].nivel,
        "id_setor": SESSIONS[token].id_setor,
    }


@app.post("/auth/logout")
def logout(data: LogoutRequest) -> dict[str, bool]:
    SESSIONS.pop(data.token, None)
    return {"ok": True}


@app.post("/chat/message")
def chat_message(data: ChatRequest) -> dict[str, Any]:
    session = SESSIONS.get(data.token)
    if not session:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")

    try:
        resposta = responder(data.mensagem, session.id_setor)
        return {"ok": True, "resposta": resposta}
    except Exception as exc:
        logger.exception("Erro ao processar mensagem")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/admin/{action}")
def admin_call(action: str, data: AdminCallRequest) -> dict[str, Any]:
    session = SESSIONS.get(data.token)
    if not session:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    if session.nivel != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    method_name = f"admin_{action}"
    if not hasattr(admin_api, method_name):
        raise HTTPException(status_code=404, detail="Acao admin nao encontrada")

    method = getattr(admin_api, method_name)
    if not callable(method):
        raise HTTPException(status_code=404, detail="Acao admin invalida")

    try:
        signature = inspect.signature(method)
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name in data.payload:
                kwargs[param_name] = data.payload[param_name]
            elif param.default is inspect._empty:
                raise HTTPException(status_code=400, detail=f"Parametro obrigatorio ausente: {param_name}")

        result = method(**kwargs)
        return {"ok": True, "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em chamada admin")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "0") == "1",
    )

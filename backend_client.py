import inspect
import json
from urllib import error, request

from admin_api import AdminAPI


class RemoteBackendError(Exception):
    pass


class BackendClient:
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None):
        url = f"{self.base_url}{path}"
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                data = response.read().decode("utf-8")
                return json.loads(data) if data else {}
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            # Se for erro 401 (Unauthorized), marca como sessão inválida
            if exc.code == 401:
                raise RemoteBackendError(f"HTTP 401: Sessao expirada ou invalida. Faca login novamente.") from exc
            raise RemoteBackendError(f"HTTP {exc.code}: {message}") from exc
        except error.URLError as exc:
            raise RemoteBackendError(f"Falha de conexao: {exc.reason}") from exc

    def login(self, usuario: str, senha: str) -> dict:
        return self._request("POST", "/auth/login", {"usuario": usuario, "senha": senha})

    def logout(self, token: str) -> dict:
        return self._request("POST", "/auth/logout", {"token": token})

    def send_chat(self, token: str, mensagem: str) -> dict:
        return self._request("POST", "/chat/message", {"token": token, "mensagem": mensagem})

    def admin_call(self, action: str, token: str, payload: dict | None = None):
        return self._request(
            "POST",
            f"/admin/{action}",
            {"token": token, "payload": payload or {}},
        )


class RemoteAdminProxy:
    def __init__(self, client: BackendClient, token_getter):
        self.client = client
        self.token_getter = token_getter
        self._signatures = {}
        for method_name in dir(AdminAPI):
            if method_name.startswith("admin_"):
                method = getattr(AdminAPI, method_name)
                if callable(method):
                    self._signatures[method_name] = inspect.signature(method)

    def __getattr__(self, method_name: str):
        if not method_name.startswith("admin_"):
            raise AttributeError(method_name)
        if method_name not in self._signatures:
            raise AttributeError(method_name)

        signature = self._signatures[method_name]

        def _caller(*args, **kwargs):
            token = self.token_getter()
            if not token:
                raise RemoteBackendError("Sessao invalida. Faca login novamente.")

            payload = dict(kwargs) if kwargs else {}
            if args:
                params = [
                    p
                    for p in signature.parameters.values()
                    if p.name != "self"
                ]
                if len(args) > len(params):
                    raise RemoteBackendError(
                        f"Argumentos invalidos para {method_name}: recebido {len(args)}"
                    )
                for idx, value in enumerate(args):
                    payload[params[idx].name] = value

            action = method_name.replace("admin_", "", 1)
            response = self.client.admin_call(action, token, payload)
            if not response.get("ok"):
                raise RemoteBackendError("Falha na chamada administrativa")
            return response.get("result")

        return _caller

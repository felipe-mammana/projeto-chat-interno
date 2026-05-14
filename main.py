from unittest import result

import webview as web
import time
import threading
import os
import sys
import logging
import json
from datetime import datetime, timedelta

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logging.warning("pywin32 não instalado — trava de posição desativada")

from app import responder as local_responder
from auth import autenticar as local_autenticar
from backend_client import BackendClient, RemoteBackendError, RemoteAdminProxy

# ==================================================
# LOGGING
# ==================================================
LOG_DIR = os.path.join(os.getenv("APPDATA"), "MeuApp")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "debug.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logging.debug("Aplicação iniciada")

SESSION_DIR = os.path.join(os.path.expanduser("~"), ".chatarqv")
SESSION_FILE = os.path.join(SESSION_DIR, "session.json")

def _ensure_session_dir():
    os.makedirs(SESSION_DIR, exist_ok=True)

def _write_session_data(payload: dict):
    _ensure_session_dir()
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def _read_session_data():
    if not os.path.isfile(SESSION_FILE):
        return None
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _delete_session_file():
    try:
        if os.path.isfile(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        logging.exception("Falha ao remover session.json")

def _config_paths():
    paths = []
    try:
        if getattr(sys, "frozen", False):
            paths.append(os.path.join(os.path.dirname(sys.executable), "config.json"))
        else:
            paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    except Exception:
        pass

    paths.append(os.path.join(os.getcwd(), "config.json"))
    return paths


def _load_remote_url():
    env_url = os.getenv("REMOTE_API_URL", "").strip()
    if env_url:
        return env_url

    for path in _config_paths():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            url = str(data.get("REMOTE_API_URL", "")).strip()
            if url:
                return url
        except Exception:
            logging.exception("Erro ao ler config.json")
            continue

    return ""


REMOTE_API_URL = _load_remote_url()
logging.info("REMOTE_API_URL=%s", REMOTE_API_URL or "LOCAL_MODE")
USE_REMOTE_API = bool(REMOTE_API_URL)
_remote_client = BackendClient(REMOTE_API_URL) if USE_REMOTE_API else None
_remote_token = None

# Importa AdminAPI local somente quando estiver em modo local
if USE_REMOTE_API:
    LocalAdminAPI = None
else:
    from admin_api import AdminAPI as LocalAdminAPI


def autenticar(usuario, senha, lembrar=False):
    global _remote_token
    if not USE_REMOTE_API:
        result = local_autenticar(usuario, senha)
    else:
        result = _remote_client.login(usuario, senha)
        if result.get("ok"):
            _remote_token = result.get("token")

    if result.get("ok") and lembrar:
        try:
            api_obj = globals().get("api")
            if api_obj and hasattr(api_obj, "salvar_sessao"):
                api_obj.salvar_sessao(
                    result.get("token"),
                    result.get("nome"),
                    result.get("nivel"),
                    result.get("id_setor"),
                )
            else:
                expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
                _write_session_data({
                    "token": result.get("token"),
                    "nome": result.get("nome"),
                    "nivel": result.get("nivel"),
                    "id_setor": result.get("id_setor"),
                    "expires_at": expires_at,
                })
        except Exception:
            logging.exception("Falha ao salvar sessao")

    if not USE_REMOTE_API:
        return result
    return {
        "ok": bool(result.get("ok")),
        "msg": result.get("detail"),
        "nome": result.get("nome"),
        "nivel": result.get("nivel"),
        "id_setor": result.get("id_setor"),
        "token": result.get("token"),
    }


def responder(texto, id_setor=None):
    global _remote_token
    if not USE_REMOTE_API:
        return local_responder(texto, id_setor)
    if not _remote_token:
        raise RemoteBackendError("Sessao invalida. Faca login novamente.")
    
    try:
        result = _remote_client.send_chat(_remote_token, texto)
        return result.get("resposta", "")
    except RemoteBackendError as e:
        # Se for erro 401, limpa a sessão e pede novo login
        if "401" in str(e) or "Sessao expirada" in str(e):
            _delete_session_file()
            _remote_token = None
            raise RemoteBackendError("Sua sessão expirou. Faça login novamente.") from e
        raise


class AdminAPI:
    def __init__(self):
        self.local_admin = LocalAdminAPI() if not USE_REMOTE_API else None
        self.remote_admin = RemoteAdminProxy(_remote_client, lambda: _remote_token) if USE_REMOTE_API else None

    def __getattr__(self, method_name):
        if not method_name.startswith("admin_"):
            raise AttributeError(method_name)

        if self.local_admin is not None:
            return getattr(self.local_admin, method_name)

        if self.remote_admin is not None:
            return getattr(self.remote_admin, method_name)

        raise AttributeError(method_name)


# ==================================================
# RESOURCE PATH
# ==================================================
def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# ==================================================
# JANELAS GLOBAIS
# ==================================================
login_window = None
chat_window = None
widget_window = None
admin_window = None

# ==================================================
# CHAT ASYNC HELPERS
# ==================================================
def _send_chat_payload(payload: dict):
    if not chat_window:
        return
    try:
        chat_window.evaluate_js(f"window.onBotResponse({json.dumps(payload)})")
    except Exception:
        logging.exception("Erro ao enviar resposta para o chat")

# ==================================================
# APP EXIT
# ==================================================
_app_closing = False

def request_app_exit():
    global _app_closing
    if _app_closing:
        return
    _app_closing = True
    try:
        logging.info("Encerrando aplicacao")
        web.stop()
    except Exception:
        pass
    finally:
        os._exit(0)


def _bind_close(window, kind="exit"):
    try:
        if kind == "exit":
            window.events.closed += request_app_exit
            return

        if hasattr(window.events, "closing"):
            def _on_closing():
                try:
                    api_obj = globals().get("api")
                    if kind == "widget":
                        if api_obj and not getattr(api_obj, "chat_aberto", False):
                            api_obj.open_chat()
                        window.hide()
                    elif kind == "chat":
                        if api_obj and getattr(api_obj, "chat_aberto", False):
                            api_obj.close_chat()
                        else:
                            window.hide()
                    elif kind == "admin":
                        if api_obj and getattr(api_obj, "admin_aberto", False):
                            api_obj.voltar_ao_chat()
                        else:
                            window.hide()
                except Exception:
                    logging.exception("Falha ao interceptar fechamento de janela")
                return False

            window.events.closing += _on_closing
        else:
            window.events.closed += request_app_exit
    except Exception:
        logging.exception("Falha ao registrar evento de fechamento")

# ==================================================
# HELPERS DE POSIÇÃO
# ==================================================
TASKBAR_HEIGHT = 48
MARGIN = 20
RIGHT_MARGIN = 20

def get_widget_position():
    screen = web.screens[0]
    WIDGET_SIZE = 60
    CLOCK_AREA_WIDTH = 140
    x = screen.width - CLOCK_AREA_WIDTH - (WIDGET_SIZE // 2)
    y = screen.height - WIDGET_SIZE - TASKBAR_HEIGHT - MARGIN
    return (x, y)

def get_chat_position():
    screen = web.screens[0]
    return (
        screen.width - 320 - RIGHT_MARGIN,
        screen.height - 520 - TASKBAR_HEIGHT - MARGIN
    )

def force_refresh(win):
    if not win:
        return
    try:
        x, y = win.x, win.y
        win.move(x + 1, y + 1)
        win.move(x, y)
    except Exception:
        pass

# ==================================================
# ANIMAÇÃO
# ==================================================
def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

def animate_move(win, start_x, start_y, end_x, end_y, duration=0.12, steps=12):
    dx = end_x - start_x
    dy = end_y - start_y
    delay = duration / steps
    win.move(start_x, start_y)
    
    for i in range(steps + 1):
        t = i / steps
        eased = ease_out_cubic(t)
        x = int(start_x + dx * eased)
        y = int(start_y + dy * eased)
        win.move(x, y)
        time.sleep(delay)

# ==================================================
# API PYWEBVIEW
# ==================================================
class API:
    def __init__(self):
        self.usuario_nome = "Usuario"
        self.usuario_tipo = "usuario"
        self.id_setor = None
        logging.info(f"SETOR DO USUÁRIO = {self.id_setor}")
        self.chat_aberto = False
        self.admin_aberto = False
        self.admin_api = AdminAPI()
        self._widget_shown = False

        # --- Trava de posição ---
        self._locked = False
        self._lock_paused = False
        self._lock_pos = (0, 0)   # (x, y) em coords de tela — via win32gui
        self._lock_hwnd = None    # handle nativo da janela
        self._lock_thread = None
        self._lock_drag_overridden = False
        self._dragging = False
        self._drag_start = (0, 0)
        self._drag_win_start = (0, 0)

    # ---------- USUÁRIO ----------
    def get_usuario(self):
        logging.debug("get_usuario chamado: %s", self.usuario_nome)
        return self.usuario_nome
    
    def get_usuario_tipo(self):
        return self.usuario_tipo

    # ---------- LOGIN ----------
    def login(self, usuario, senha, lembrar=False):
        logging.debug("Tentativa de login: %s", usuario)

        try:
            result = autenticar(usuario, senha, lembrar)
        except RemoteBackendError as exc:
            logging.exception("Erro ao autenticar via API remota")
            return {"success": False, "message": str(exc)}
        except Exception:
            logging.exception("Erro ao autenticar")
            return {"success": False, "message": "Erro interno no login"}

        if not result.get("ok"):
            return {"success": False, "message": result.get("msg")}

        self.usuario_nome = result.get("nome", "Usuario")
        self.usuario_tipo = result.get("nivel", "usuario")
        self.id_setor = result.get("id_setor")

        logging.info(f"LOGIN OK - USUARIO={self.usuario_nome} TIPO={self.usuario_tipo} SETOR={self.id_setor}")

        self.login_success()
        return {"success": True, "tipo": self.usuario_tipo}

    # ---------- SESSÃO ----------
    def salvar_sessao(self, token, nome, nivel, id_setor):
        try:
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
            payload = {
                "token": token,
                "nome": nome,
                "nivel": nivel,
                "id_setor": id_setor,
                "expires_at": expires_at,
            }
            _write_session_data(payload)
            logging.info("Sessao salva com expiracao em %s", expires_at)
            return {"ok": True}
        except Exception:
            logging.exception("Falha ao salvar sessao")
            return {"ok": False}

    def verificar_sessao(self):
        global _remote_token
        try:
            data = _read_session_data()
            if not data:
                return {"valido": False}

            expires_at = data.get("expires_at")
            if not expires_at:
                _delete_session_file()
                return {"valido": False}

            try:
                exp_dt = datetime.fromisoformat(expires_at)
            except Exception:
                _delete_session_file()
                return {"valido": False}

            if datetime.utcnow() > exp_dt:
                _delete_session_file()
                return {"valido": False}

            if USE_REMOTE_API and not data.get("token"):
                return {"valido": False}

            self.usuario_nome = data.get("nome") or "Usuario"
            self.usuario_tipo = data.get("nivel") or "usuario"
            self.id_setor = data.get("id_setor")

            if USE_REMOTE_API:
                _remote_token = data.get("token")

            self.login_success()
            return {
                "valido": True,
                "nome": self.usuario_nome,
                "nivel": self.usuario_tipo,
                "id_setor": self.id_setor,
                "token": data.get("token"),
            }
        except Exception:
            logging.exception("Erro ao verificar sessao")
            return {"valido": False}

    def logout_sessao(self):
        _delete_session_file()
        return {"ok": True}

    def logout(self):
        global _remote_token, chat_window, widget_window, admin_window, login_window
        try:
            self.logout_sessao()
            _remote_token = None

            # Reset user state
            self.usuario_nome = "Usuario"
            self.usuario_tipo = "usuario"
            self.id_setor = None
            self.chat_aberto = False
            self.admin_aberto = False

            # Unlock window if needed
            if self._locked:
                self._locked = False
                self._set_drag_enabled(True)

            if admin_window:
                admin_window.hide()
            if chat_window:
                chat_window.hide()
                chat_window.on_top = False
            if widget_window:
                widget_window.hide()

            if login_window:
                login_window.show()
                login_window.on_top = True
                try:
                    # Ensure login UI becomes visible when window is shown again
                    login_window.evaluate_js(
                        "try { if (typeof mostrarLogin === 'function') { mostrarLogin(); } "
                        "else { const c=document.querySelector('.login-container'); if (c) c.style.visibility='visible'; } } catch(e) {}"
                    )
                except Exception:
                    pass
                force_refresh(login_window)

            return {"ok": True}
        except Exception:
            logging.exception("Erro ao fazer logout")
            return {"ok": False}

    # ---------- CHAT ----------
    def enviar_mensagem(self, mensagem):
        logging.debug("Mensagem recebida de %s: %s", self.usuario_nome, mensagem)

        try:
            resposta = responder(mensagem, self.id_setor)
            logging.debug("Resposta gerada com sucesso")
            return {"ok": True, "resposta": resposta}
        except RemoteBackendError as exc:
            logging.exception("Erro ao processar mensagem via API remota")
            return {"ok": False, "resposta": str(exc)}
        except Exception:
            logging.exception("Erro ao processar mensagem")
            return {"ok": False, "resposta": "Erro interno ao processar mensagem"}

    def enviar_mensagem_async(self, mensagem):
        logging.debug("Mensagem recebida (async) de %s: %s", self.usuario_nome, mensagem)

        def _run():
            try:
                resposta = responder(mensagem, self.id_setor)
                payload = {"ok": True, "resposta": resposta}
            except RemoteBackendError as exc:
                logging.exception("Erro ao processar mensagem via API remota (async)")
                payload = {"ok": False, "resposta": str(exc)}
            except Exception:
                logging.exception("Erro ao processar mensagem (async)")
                payload = {"ok": False, "resposta": "Erro interno ao processar mensagem"}

            _send_chat_payload(payload)

        threading.Thread(target=_run, daemon=True).start()
        return {"ok": True}

    # ---------- WIDGET ----------
    
    # ==================================================
    # TRAVAR POSIÇÃO DA JANELA
    # ==================================================
    def _get_hwnd(self):
        """Encontra o HWND nativo da janela de chat via win32gui."""
        if not HAS_WIN32:
            return None
        try:
            # Pega o PID do processo atual e encontra janelas dele
            import win32process
            import win32api
            cur_pid = os.getpid()
            found = []

            def _cb(hwnd, _):
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == cur_pid:
                    found.append(hwnd)
                return True

            win32gui.EnumWindows(_cb, None)

            # Filtra pela janela de chat (320x520)
            for hwnd in found:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if abs(w - 320) < 20 and abs(h - 520) < 20:
                        return hwnd
                except Exception:
                    continue
            # Fallback: pega o primeiro
            return found[0] if found else None
        except Exception:
            logging.exception("Erro ao encontrar hwnd")
            return None

    def toggle_lock(self, lock: bool):
        """Trava ou destrava a posição da janela do chat."""
        self._locked = bool(lock)

        if self._locked:
            # Captura posição real via win32gui
            hwnd = self._get_hwnd()
            self._lock_hwnd = hwnd
            if hwnd and HAS_WIN32:
                rect = win32gui.GetWindowRect(hwnd)
                self._lock_pos = (rect[0], rect[1])
            elif chat_window:
                self._lock_pos = (chat_window.x, chat_window.y)
            logging.info(f"Janela travada em {self._lock_pos} hwnd={self._lock_hwnd}")

            # Desabilita o "easy drag" do pywebview para evitar movimentação
            # e tremor enquanto estiver travado.
            self._set_drag_enabled(False)

            if self._lock_thread is None or not self._lock_thread.is_alive():
                self._lock_thread = threading.Thread(
                    target=self._enforce_position,
                    daemon=True
                )
                self._lock_thread.start()
        else:
            logging.info("Janela destravada")
            self._set_drag_enabled(True)

        return {"ok": True}

    def set_lock_paused(self, paused: bool):
        """Chamado pelo JS: mouse entrou (pausa) ou saiu (reativa)."""
        self._lock_paused = bool(paused)
        return {"ok": True}

    def _set_drag_enabled(self, enabled: bool):
        """Ativa/desativa o drag do body no Chromium.
        Remove tremor ao bloquear a janela."""
        global chat_window
        if not chat_window:
            return
        try:
            if enabled:
                # Limpa override para voltar ao comportamento padrão do pywebview
                chat_window.evaluate_js("document.body.style.webkitAppRegion = ''")
                self._lock_drag_overridden = False
            else:
                chat_window.evaluate_js("document.body.style.webkitAppRegion = 'no-drag'")
                self._lock_drag_overridden = True
        except Exception:
            logging.exception("Falha ao alternar drag do body")

    def drag_start(self, screen_x: int, screen_y: int):
        """Inicia o arrasto manual da janela (quando destravada)."""
        if self._locked:
            return {"ok": False}
        self._dragging = True
        self._drag_start = (int(screen_x), int(screen_y))

        hwnd = self._get_hwnd()
        self._lock_hwnd = hwnd
        if hwnd and HAS_WIN32:
            rect = win32gui.GetWindowRect(hwnd)
            self._drag_win_start = (rect[0], rect[1])
        elif chat_window:
            self._drag_win_start = (chat_window.x, chat_window.y)
        return {"ok": True}

    def drag_move(self, screen_x: int, screen_y: int):
        """Move a janela manualmente durante o arrasto."""
        if self._locked or not self._dragging:
            return {"ok": False}

        sx, sy = self._drag_start
        wx, wy = self._drag_win_start
        dx = int(screen_x) - sx
        dy = int(screen_y) - sy
        nx = wx + dx
        ny = wy + dy

        if HAS_WIN32 and self._lock_hwnd:
            win32gui.SetWindowPos(
                self._lock_hwnd,
                0,
                nx, ny, 0, 0,
                win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER
            )
        elif chat_window:
            chat_window.move(nx, ny)
        return {"ok": True}

    def drag_end(self):
        """Finaliza o arrasto manual da janela."""
        self._dragging = False
        return {"ok": True}

    def _enforce_position(self):
        """Usa win32gui para ler e forçar a posição real da janela.
        Enquanto pausado (mouse dentro), não faz nada — sem tremido."""
        global chat_window

        while self._locked:
            try:
                if not self._lock_paused and self._locked:
                    tx, ty = self._lock_pos

                    if HAS_WIN32 and self._lock_hwnd:
                        # Lê posição real do SO — sem depender do pywebview
                        rect = win32gui.GetWindowRect(self._lock_hwnd)
                        cx, cy = rect[0], rect[1]
                        dx = abs(cx - tx)
                        dy = abs(cy - ty)
                        if dx > 5 or dy > 5:
                            # Move de volta usando win32 diretamente
                            win32gui.SetWindowPos(
                                self._lock_hwnd,
                                0,
                                tx, ty, 0, 0,
                                win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER
                            )
                    elif chat_window:
                        # Fallback sem win32
                        dx = abs(chat_window.x - tx)
                        dy = abs(chat_window.y - ty)
                        if dx > 5 or dy > 5:
                            chat_window.move(tx, ty)
            except Exception:
                pass

            time.sleep(0.1)

    # ==================================================
    # JANELAS
    # ==================================================
    def login_success(self):
        global chat_window, widget_window, login_window

        logging.debug("Login success - criando janelas")

        if login_window:
            login_window.hide()

        # Criar janela de chat
        chat_window = web.create_window(
            "",
            resource_path("chat.html"),
            width=320,
            height=520,
            frameless=True,
            resizable=False,
            on_top=True,
            background_color="#000000",
            js_api=self,
            easy_drag=False,
            hidden=True
        )
        _bind_close(chat_window, kind="chat")

        wx, wy = get_widget_position()

        # Criar widget - já na posição correta e visível
        widget_window = web.create_window(
            "",
            resource_path("widget.html"),
            width=60,
            height=60,
            x=wx,
            y=wy,
            frameless=True,
            transparent=True,
            background_color="#000000",
            resizable=False,
            on_top=True,
            js_api=self,
            easy_drag=False,
            hidden=False
        )
        _bind_close(widget_window, kind="widget")
        self.chat_aberto = False

    def widget_ready(self):
        # Não precisa fazer nada - widget já está mostrado na criação
        self._widget_shown = True
        logging.debug("✅ Widget carregado")

    

    def criar_janela_admin(self):
        global admin_window, chat_window, widget_window

        # Destrava antes de fechar/mover o chat
        if self._locked:
            self._locked = False
            self._set_drag_enabled(True)

        if chat_window and self.chat_aberto:
            self.close_chat()

        if widget_window:
            widget_window.on_top = False
            widget_window.hide()

        screen = web.screens[0]

        admin_window = web.create_window(
            "ClínicaApp - Painel Administrativo",
            resource_path("painel_admin.html"),
            width=screen.width,
            height=screen.height,
            x=0,
            y=0,
            resizable=True,
            js_api=self,
            hidden=False
        )
        _bind_close(admin_window, kind="admin")

        admin_window.maximize()
        admin_window.on_top = True

        self.admin_aberto = True

    def voltar_ao_chat(self):
        global admin_window, widget_window

        logging.debug("Voltando ao chat")

        if admin_window:
            admin_window.hide()
            self.admin_aberto = False

        if widget_window:
            widget_window.show()
            widget_window.on_top = True
            force_refresh(widget_window)

        self.open_chat()

    # ---------- ABRIR CHAT ----------
    def open_chat(self):
        global chat_window, widget_window

        if self.chat_aberto:
            return

        logging.debug("Abrindo chat")
        self.chat_aberto = True

        wx, wy = get_widget_position()
        cx, cy = get_chat_position()

        if widget_window:
            widget_window.on_top = False
            widget_window.hide()

        if chat_window:
            chat_window.show()
            chat_window.on_top = True
            animate_move(chat_window, wx + 20, wy + 20, cx, cy)
            chat_window.evaluate_js(
                f'document.getElementById("nome-usuario").innerText = "{self.usuario_nome}";'
            )
            force_refresh(chat_window)

    # ---------- FECHAR CHAT ----------
    def close_chat(self):
        global chat_window, widget_window

        if not self.chat_aberto:
            return

        logging.debug("Fechando chat")

        # Destrava automaticamente ao fechar
        if self._locked:
            self._locked = False
            logging.info("Trava removida ao fechar o chat")
            self._set_drag_enabled(True)

        self.chat_aberto = False

        wx, wy = get_widget_position()
        cx, cy = get_chat_position()

        if chat_window:
            animate_move(chat_window, cx, cy, wx + 20, wy + 20)
            chat_window.hide()
            chat_window.on_top = False

        if widget_window:
            widget_window.move(wx, wy)
            widget_window.show()
            for _ in range(2):
                time.sleep(0.01)
                force_refresh(widget_window)
            widget_window.on_top = True

    def abrir_painel_admin(self):
        """Abre o painel administrativo somente se for admin"""
        if self.usuario_tipo != "admin":
            logging.warning("Tentativa de acesso ao painel admin por usuário não-admin")
            return {"ok": False, "msg": "Acesso negado"}

        logging.debug("Abrindo painel admin via abrir_painel_admin")
        self.criar_janela_admin()
        return {"ok": True}

    # ==================================================
    # MÉTODOS ADMIN - MÉDICOS
    # ==================================================
    def admin_contar_medicos(self):
        try:
            return self.admin_api.admin_contar_medicos()
        except Exception as e:
            logging.exception("Erro ao contar médicos")
            raise

    def admin_listar_medicos(self):
        try:
            return self.admin_api.admin_listar_medicos()
        except Exception as e:
            logging.exception("Erro ao listar médicos")
            raise

    def admin_obter_medico(self, id):
        try:
            return self.admin_api.admin_obter_medico(id)
        except Exception as e:
            logging.exception("Erro ao obter médico")
            raise

    def admin_criar_medico(self, nome, crm, ativo):
        try:
            return self.admin_api.admin_criar_medico(nome, crm, ativo)
        except Exception as e:
            logging.exception("Erro ao criar médico")
            raise

    def admin_editar_medico(self, id, nome, crm, ativo):
        try:
            return self.admin_api.admin_editar_medico(id, nome, crm, ativo)
        except Exception as e:
            logging.exception("Erro ao editar médico")
            raise

    def admin_excluir_medico(self, id):
        try:
            return self.admin_api.admin_excluir_medico(id)
        except Exception as e:
            logging.exception("Erro ao excluir médico")
            raise

    # ==================================================
    # MÉTODOS ADMIN - REGRAS E PROCEDIMENTOS DO MÉDICO
    # ==================================================
    def admin_obter_medico_regras(self, medico_id):
        try:
            return self.admin_api.admin_obter_medico_regras(medico_id)
        except Exception as e:
            logging.exception("Erro ao obter regras médico")
            raise

    def admin_salvar_medico_regras(self, medico_id, imc_geral, imc_mama_redutora, imc_pos_bariatrica,
                                    max_cirurgias_combinadas, indicacao_cirurgica, observacoes):
        try:
            return self.admin_api.admin_salvar_medico_regras(
                medico_id, imc_geral, imc_mama_redutora, imc_pos_bariatrica,
                max_cirurgias_combinadas, indicacao_cirurgica, observacoes
            )
        except Exception as e:
            logging.exception("Erro ao salvar regras médico")
            raise

    def admin_obter_medico_procedimentos(self, medico_id):
        try:
            return self.admin_api.admin_obter_medico_procedimentos(medico_id)
        except Exception as e:
            logging.exception("Erro ao obter procedimentos médico")
            raise

    def admin_salvar_medico_procedimentos(self, medico_id, procedimentos):
        try:
            return self.admin_api.admin_salvar_medico_procedimentos(medico_id, procedimentos)
        except Exception as e:
            logging.exception("Erro ao salvar procedimentos médico")
            raise

    # ==================================================
    # MÉTODOS ADMIN - FUNCIONÁRIOS
    # ==================================================
    def admin_listar_funcionarios(self):
        try:
            return self.admin_api.admin_listar_funcionarios()
        except Exception as e:
            logging.exception("Erro ao listar funcionários")
            raise

    def admin_obter_funcionario(self, id):
        try:
            return self.admin_api.admin_obter_funcionario(id)
        except Exception as e:
            logging.exception("Erro ao obter funcionário")
            raise

    def admin_criar_funcionario(self, nome, email, ramal, setor_id, ativo):
        try:
            return self.admin_api.admin_criar_funcionario(nome, email, ramal, setor_id, ativo)
        except Exception as e:
            logging.exception("Erro ao criar funcionário")
            raise

    def admin_editar_funcionario(self, id, nome, email, ramal, setor_id, ativo):
        try:
            return self.admin_api.admin_editar_funcionario(id, nome, email, ramal, setor_id, ativo)
        except Exception as e:
            logging.exception("Erro ao editar funcionário")
            raise

    def admin_excluir_funcionario(self, id):
        try:
            return self.admin_api.admin_excluir_funcionario(id)
        except Exception as e:
            logging.exception("Erro ao excluir funcionário")
            raise

    # ==================================================
    # MÉTODOS ADMIN - SETORES
    # ==================================================
    def admin_listar_setores(self):
        try:
            return self.admin_api.admin_listar_setores()
        except Exception as e:
            logging.exception("Erro ao listar setores")
            raise

    def admin_obter_setor(self, id):
        try:
            return self.admin_api.admin_obter_setor(id)
        except Exception as e:
            logging.exception("Erro ao obter setor")
            raise

    def admin_criar_setor(self, nome):
        try:
            return self.admin_api.admin_criar_setor(nome)
        except Exception as e:
            logging.exception("Erro ao criar setor")
            raise

    def admin_editar_setor(self, id, nome):
        try:
            return self.admin_api.admin_editar_setor(id, nome)
        except Exception as e:
            logging.exception("Erro ao editar setor")
            raise

    def admin_excluir_setor(self, id):
        try:
            return self.admin_api.admin_excluir_setor(id)
        except Exception as e:
            logging.exception("Erro ao excluir setor")
            raise

    # ==================================================
    # MÉTODOS ADMIN - PROCEDIMENTOS
    # ==================================================
    def admin_listar_procedimentos(self):
        try:
            return self.admin_api.admin_listar_procedimentos()
        except Exception as e:
            logging.exception("Erro ao listar procedimentos")
            raise

    def admin_obter_procedimento(self, id):
        try:
            return self.admin_api.admin_obter_procedimento(id)
        except Exception as e:
            logging.exception("Erro ao obter procedimento")
            raise

    def admin_criar_procedimento(self, nome):
        try:
            return self.admin_api.admin_criar_procedimento(nome)
        except Exception as e:
            logging.exception("Erro ao criar procedimento")
            raise

    def admin_editar_procedimento(self, id, nome):
        try:
            return self.admin_api.admin_editar_procedimento(id, nome)
        except Exception as e:
            logging.exception("Erro ao editar procedimento")
            raise

    def admin_excluir_procedimento(self, id):
        try:
            return self.admin_api.admin_excluir_procedimento(id)
        except Exception as e:
            logging.exception("Erro ao excluir procedimento")
            raise

    # ==================================================
    # MÉTODOS ADMIN - CNN DUPLAS
    # ==================================================
    def admin_listar_cnn_duplas(self):
        try:
            return self.admin_api.admin_listar_cnn_duplas()
        except Exception as e:
            logging.exception("Erro ao listar CNN duplas")
            raise

    def admin_obter_cnn_dupla(self, id):
        try:
            return self.admin_api.admin_obter_cnn_dupla(id)
        except Exception as e:
            logging.exception("Erro ao obter CNN dupla")
            raise

    def admin_criar_cnn_dupla(self, codigo_cnn, nome, procedimentos):
        try:
            return self.admin_api.admin_criar_cnn_dupla(codigo_cnn, nome, procedimentos)
        except Exception as e:
            logging.exception("Erro ao criar CNN dupla")
            raise

    def admin_editar_cnn_dupla(self, id, codigo_cnn, nome, procedimentos):
        try:
            return self.admin_api.admin_editar_cnn_dupla(id, codigo_cnn, nome, procedimentos)
        except Exception as e:
            logging.exception("Erro ao editar CNN dupla")
            raise

    def admin_excluir_cnn_dupla(self, id):
        try:
            return self.admin_api.admin_excluir_cnn_dupla(id)
        except Exception as e:
            logging.exception("Erro ao excluir CNN dupla")
            raise

    # ==================================================
    # MÉTODOS ADMIN - TIPOS DE ATENDIMENTO
    # ==================================================
    def admin_listar_tipos_atendimento(self):
        try:
            return self.admin_api.admin_listar_tipos_atendimento()
        except Exception as e:
            logging.exception("Erro ao listar tipos de atendimento")
            raise

    def admin_obter_tipo_atendimento(self, id):
        try:
            return self.admin_api.admin_obter_tipo_atendimento(id)
        except Exception as e:
            logging.exception("Erro ao obter tipo de atendimento")
            raise

    def admin_criar_tipo_atendimento(self, nome):
        try:
            return self.admin_api.admin_criar_tipo_atendimento(nome)
        except Exception as e:
            logging.exception("Erro ao criar tipo de atendimento")
            raise

    def admin_editar_tipo_atendimento(self, id, nome):
        try:
            return self.admin_api.admin_editar_tipo_atendimento(id, nome)
        except Exception as e:
            logging.exception("Erro ao editar tipo de atendimento")
            raise

    def admin_excluir_tipo_atendimento(self, id):
        try:
            return self.admin_api.admin_excluir_tipo_atendimento(id)
        except Exception as e:
            logging.exception("Erro ao excluir tipo de atendimento")
            raise

    # ==================================================
    # MÉTODOS ADMIN - AGENDA MÉDICO
    # ==================================================
    def admin_listar_agenda_medico(self, medico_id=None):
        try:
            return self.admin_api.admin_listar_agenda_medico(medico_id)
        except Exception as e:
            logging.exception("Erro ao listar agenda médico")
            raise

    def admin_obter_agenda_medico(self, id):
        try:
            return self.admin_api.admin_obter_agenda_medico(id)
        except Exception as e:
            logging.exception("Erro ao obter agenda médico")
            raise

    def admin_criar_agenda_medico(self, medico_id, dia_semana, hora_inicio, hora_fim, atendimentos):
        try:
            return self.admin_api.admin_criar_agenda_medico(medico_id, dia_semana, hora_inicio, hora_fim, atendimentos)
        except Exception as e:
            logging.exception("Erro ao criar agenda médico")
            raise

    def admin_editar_agenda_medico(self, id, medico_id, dia_semana, hora_inicio, hora_fim, atendimentos):
        try:
            return self.admin_api.admin_editar_agenda_medico(id, medico_id, dia_semana, hora_inicio, hora_fim, atendimentos)
        except Exception as e:
            logging.exception("Erro ao editar agenda médico")
            raise

    def admin_excluir_agenda_medico(self, id):
        try:
            return self.admin_api.admin_excluir_agenda_medico(id)
        except Exception as e:
            logging.exception("Erro ao excluir agenda médico")
            raise

    # ==================================================
    # MÉTODOS ADMIN - LOGINS
    # ==================================================
    def admin_listar_logins(self):
        try:
            return self.admin_api.admin_listar_logins()
        except Exception as e:
            logging.exception("Erro ao listar logins")
            raise

    def admin_obter_login(self, id):
        try:
            return self.admin_api.admin_obter_login(id)
        except Exception as e:
            logging.exception("Erro ao obter login")
            raise

    def admin_criar_login(self, funcionario_id, usuario, senha, nivel, ativo):
        try:
            return self.admin_api.admin_criar_login(funcionario_id, usuario, senha, nivel, ativo)
        except Exception as e:
            logging.exception("Erro ao criar login")
            raise

    def admin_editar_login(self, id, funcionario_id, usuario, senha, nivel, ativo):
        try:
            return self.admin_api.admin_editar_login(id, funcionario_id, usuario, senha, nivel, ativo)
        except Exception as e:
            logging.exception("Erro ao editar login")
            raise

    def admin_excluir_login(self, id):
        try:
            return self.admin_api.admin_excluir_login(id)
        except Exception as e:
            logging.exception("Erro ao excluir login")
            raise


# ==================================================
# START
# ==================================================
api = API()

if __name__ == "__main__":
    logging.debug("Criando janela de login")

    login_window = web.create_window(
        "Login",
        resource_path("login.html"),
        width=800,
        height=540,
        frameless=True,
        transparent=True,
        resizable=False,
        js_api=api
    )
    _bind_close(login_window, kind="exit")

    web.start(gui="edgechromium", private_mode=True)

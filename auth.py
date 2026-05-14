import logging

import bcrypt

from db import get_conn

# ==================================
# HASH DE SENHA
# ==================================

def gerar_hash(senha: str) -> bytes:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())


def verificar_hash(senha_digitada: str, senha_hash_db: bytes) -> bool:
    return bcrypt.checkpw(senha_digitada.encode("utf-8"), senha_hash_db)


logger = logging.getLogger(__name__)


# ==================================
# AUTENTICAR USUARIO (COM HASH)
# ==================================

def autenticar(usuario, senha):
    try:
        conn = get_conn()
    except Exception:
        logger.exception("Erro ao conectar no banco")
        return {"ok": False, "msg": "Erro ao conectar no banco"}

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT l.id, l.senha, l.nivel, l.ativo, l.funcionario_id, f.setor_id
            FROM logins l
            LEFT JOIN funcionarios f ON f.id = l.funcionario_id
            WHERE l.usuario = %s
            LIMIT 1
        """,
            (usuario,),
        )

        row = cursor.fetchone()

        if not row:
            logger.info("Usuario nao encontrado")
            return {"ok": False, "msg": "Usuario nao encontrado"}

        login_id, senha_db, nivel, ativo, funcionario_id, setor_id = row

        logger.debug("Hash banco carregado. Tipo=%s", type(senha_db))

        if ativo != 1:
            logger.info("Usuario desativado")
            return {"ok": False, "msg": "Usuario desativado"}

        if isinstance(senha_db, bytes):
            senha_db = senha_db.decode()

        if not senha_db.startswith("$2"):
            logger.warning("Hash nao e bcrypt")
            return {"ok": False, "msg": "Hash invalido no banco"}

        check = bcrypt.checkpw(senha.encode(), senha_db.encode())
        logger.debug("Resultado bcrypt=%s", check)

        if not check:
            logger.info("Senha incorreta")
            return {"ok": False, "msg": "Senha incorreta"}

        cursor.execute("SELECT nome FROM funcionarios WHERE id=%s", (funcionario_id,))
        funcionario = cursor.fetchone()

        if not funcionario:
            logger.info("Funcionario nao encontrado")
            return {"ok": False, "msg": "Funcionario nao encontrado"}

        logger.info("Login OK")

        return {
            "ok": True,
            "nivel": nivel,
            "nome": funcionario[0],
            "id_setor": setor_id,
        }
    except Exception:
        logger.exception("Erro interno ao autenticar")
        return {"ok": False, "msg": "Erro interno ao autenticar"}
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ==================================
# CRIAR USUARIO (COM HASH)
# ==================================

def criar_usuario(usuario, senha, funcionario_id, nivel="usuario"):
    try:
        conn = get_conn()
        cur = conn.cursor()

        senha_hash = gerar_hash(senha)

        cur.execute(
            """
            INSERT INTO logins (usuario, senha, funcionario_id, nivel, ativo)
            VALUES (%s, %s, %s, %s, 1)
        """,
            (usuario, senha_hash.decode("utf-8"), funcionario_id, nivel),
        )

        conn.commit()
        user_id = cur.lastrowid
        cur.close()
        conn.close()

        return {"ok": True, "msg": "Usuario criado com sucesso", "id": user_id}

    except Exception as e:
        logger.exception("Erro criar usuario")
        return {"ok": False, "msg": f"Erro ao criar usuario: {str(e)}"}


# ==================================
# ALTERAR SENHA (COM HASH)
# ==================================

def alterar_senha(usuario, senha_antiga, senha_nova):
    try:
        auth = autenticar(usuario, senha_antiga)

        if not auth["ok"]:
            return {"ok": False, "msg": "Senha atual incorreta"}

        conn = get_conn()
        cur = conn.cursor()

        nova_hash = gerar_hash(senha_nova)

        cur.execute(
            """
            UPDATE logins
            SET senha = %s
            WHERE usuario = %s
        """,
            (nova_hash.decode("utf-8"), usuario),
        )

        conn.commit()
        cur.close()
        conn.close()

        return {"ok": True, "msg": "Senha alterada com sucesso"}

    except Exception as e:
        logger.exception("Erro alterar senha")
        return {"ok": False, "msg": f"Erro ao alterar senha: {str(e)}"}


# ==================================
# VERIFICAR PERMISSAO
# ==================================

def verificar_permissao(usuario, nivel_minimo="usuario"):
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT nivel, ativo
            FROM logins
            WHERE usuario = %s
        """,
            (usuario,),
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or row[1] != 1:
            return False

        nivel_usuario = row[0]

        hierarquia = {"usuario": 0, "gerente": 1, "admin": 2}

        return hierarquia.get(nivel_usuario, 0) >= hierarquia.get(nivel_minimo, 0)

    except Exception:
        logger.exception("Erro permissao")
        return False

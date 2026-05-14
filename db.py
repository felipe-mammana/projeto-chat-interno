import os

import mysql.connector
from mysql.connector import pooling

_POOL = None


def _db_config() -> dict:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "clinica"),
        "charset": "utf8mb4",
    }


def _get_pool():
    global _POOL
    if _POOL is None:
        _POOL = pooling.MySQLConnectionPool(
            pool_name=os.getenv("DB_POOL_NAME", "clinica_pool"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            **_db_config(),
        )
    return _POOL


def get_conn():
    use_pool = os.getenv("DB_USE_POOL", "1") == "1"
    if use_pool:
        return _get_pool().get_connection()
    return mysql.connector.connect(**_db_config())


def test_connection() -> tuple[bool, str]:
    try:
        conn = get_conn()
        conn.close()
        return True, "Conexao com banco OK"
    except mysql.connector.Error as err:
        return False, f"Erro ao conectar no banco: {err}"

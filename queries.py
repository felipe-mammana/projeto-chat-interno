from db import get_conn

# ==========================================================
# FUNCIONÁRIOS
# ==========================================================
def buscar_funcionario(texto):
    texto = texto.lower()

    quer_ramal = any(p in texto for p in ["ramal", "telefone", "contato"])
    quer_email = "email" in texto
    palavras = texto.split()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.nome, f.ramal, f.email, f.ativo, s.nome
        FROM funcionarios f
        LEFT JOIN setores s ON f.setor_id = s.id
    """)
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    matches = []
    for nome, ramal, email, ativo, setor in dados:
        base = f"{nome} {setor or ''}".lower()
        score = sum(1 for p in palavras if p in base)
        if score > 0:
            matches.append((score, nome, ramal, email, ativo, setor))

    matches.sort(reverse=True)
    return matches, quer_ramal, quer_email


# ==========================================================
# MÉDICOS
# ==========================================================
def buscar_medico(nome_busca):
    nome_busca = nome_busca.lower()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM medicos")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    return [(id_, nome) for id_, nome in dados if nome_busca in nome.lower()]


def crm_medico(medico_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT crm FROM medicos WHERE id = %s",
        (medico_id,)
    )
    dado = cursor.fetchone()
    cursor.close()
    conn.close()
    return dado[0] if dado else None


# ==========================================================
# REGRAS MÉDICAS
# ==========================================================
def regras_medico_por_id(medico_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT imc_geral,
               imc_mama_redutora,
               imc_pos_bariatrica,
               observacoes,
               indicacao_cirurgica
        FROM medico_regras
        WHERE medico_id = %s
    """, (medico_id,))
    dados = cursor.fetchone()
    cursor.close()
    conn.close()
    return dados


# ==========================================================
# AGENDA
# ==========================================================
def agenda_medico(nome_medico):
    nome_medico = nome_medico.lower()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.nome, a.dia_semana, a.hora_inicio, a.hora_fim, t.nome
        FROM agenda_medico a
        JOIN medicos m ON m.id = a.medico_id
        JOIN agenda_atendimento aa ON aa.agenda_id = a.id
        JOIN tipos_atendimento t ON t.id = aa.atendimento_id
    """)
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        (dia, h1, h2, tipo)
        for nome, dia, h1, h2, tipo in dados
        if nome_medico in nome.lower()
    ]


# ==========================================================
# PROCEDIMENTOS
# ==========================================================
def procedimentos_do_medico(medico_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nome
        FROM medico_procedimento mp
        JOIN procedimentos p ON p.id = mp.procedimento_id
        WHERE mp.medico_id = %s
        ORDER BY p.nome
    """, (medico_id,))
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return [nome for (nome,) in dados]


def procedimentos_ids_do_medico(medico_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT procedimento_id
        FROM medico_procedimento
        WHERE medico_id = %s
    """, (medico_id,))
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return [p[0] for p in dados]


# ==========================================================
# CNN DUPLAS
# ==========================================================
def itens_da_cnn_dupla(duplo_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT procedimento_id
        FROM procedimento_duplo_itens
        WHERE duplo_id = %s
    """, (duplo_id,))
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return [p[0] for p in dados]


def medico_faz_cnn_dupla(medico_id, duplo_id):
    itens = itens_da_cnn_dupla(duplo_id)
    procedimentos = procedimentos_ids_do_medico(medico_id)
    return all(item in procedimentos for item in itens)


def buscar_duplos_do_medico(medico_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT c.codigo_cnn, c.nome
        FROM cnn_dupla c
        JOIN procedimento_duplo_itens pdi ON pdi.duplo_id = c.id
        JOIN medico_procedimento mp ON mp.procedimento_id = pdi.procedimento_id
        WHERE mp.medico_id = %s
        ORDER BY c.codigo_cnn
    """, (medico_id,))
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return dados


def medico_faz_cnn_dupla_por_nome(medico_id, nome_dupla):
    nome_dupla = nome_dupla.lower()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, codigo_cnn, nome FROM cnn_dupla")
    duplas = cursor.fetchall()
    cursor.close()
    conn.close()

    for duplo_id, codigo, nome in duplas:
        if nome_dupla in nome.lower():
            return (codigo, nome) if medico_faz_cnn_dupla(medico_id, duplo_id) else None

    return None


def buscar_cnn_por_nome(nome):
    nome = nome.lower()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo_cnn, nome FROM cnn_dupla")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    for codigo, nome_dupla in dados:
        if nome in nome_dupla.lower():
            return codigo, nome_dupla

    return None
# ==========================================================
# BASE DE DADOS SETORES
# ==========================================================
def buscar_base_setor(texto, id_setor):
    palavras = texto.split()

    conn = get_conn()
    cursor = conn.cursor()

    for p in palavras:
        cursor.execute("""
            SELECT resposta
            FROM chatbot_base_setor
            WHERE (pergunta LIKE %s OR palavras_chave LIKE %s)
            AND id_setor = %s
            LIMIT 1
        """, (f"%{p}%", f"%{p}%", id_setor))

        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]

    conn.close()
    return None
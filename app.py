from queries import *
import re
import unicodedata
from rapidfuzz import fuzz


estado = {
    "medico_atual": None,
    "esperando_procedimentos": False,
    "esperando_duplos": False
}


# ==========================================================
# UTILITÁRIOS
# ==========================================================

def remover_acentos(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def normalizar(texto):
    texto = texto.lower().strip()
    texto = re.sub(r"[^\w\s\+\-áéíóúãõâêôç]", "", texto)
    return texto


def limpar_nome(texto, palavras):
    for p in palavras:
        texto = re.sub(rf'\b{re.escape(p)}\b\.?', '', texto, flags=re.IGNORECASE)
    return texto.strip()


def similaridade(a, b):
    a = remover_acentos(a.lower())
    b = remover_acentos(b.lower())
    return fuzz.partial_ratio(a, b)


def match_iniciais(busca, nome):
    iniciais = "".join(p[0] for p in nome.split() if p)
    return remover_acentos(busca.upper()) == remover_acentos(iniciais.upper())


# ==========================================================
# BUSCAS MELHORADAS
# ==========================================================

def buscar_medico_inteligente(nome_busca, threshold=75, listar_todos=False):
    # Se lista_todos=True, retorna todos os médicos
    if listar_todos:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM medicos ORDER BY nome")
        dados = cursor.fetchall()
        cursor.close()
        conn.close()
        return [(id_, nome) for id_, nome in dados]
    
    if not nome_busca or len(nome_busca.strip()) < 1:
        return []

    nome_busca_norm = remover_acentos(nome_busca.lower())

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM medicos")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    resultados = []
    for id_, nome in dados:
        nome_norm = remover_acentos(nome.lower())
        palavras_nome = nome_norm.split()

        # Prioridade 1: Correspondência exata (nome inteiro)
        if nome_busca_norm == nome_norm:
            resultados.append((id_, nome, 100))
            continue

        # Prioridade 2: Palavra inteira no início (ex: busca "Leonardo" em "Dr. Leonardo Ferraro")
        if any(palavra_nome.startswith(nome_busca_norm) for palavra_nome in palavras_nome):
            resultados.append((id_, nome, 95))
            continue

        # Prioridade 3: Correspondência por iniciais (ex: "JS" → "João Silva")
        if match_iniciais(nome_busca_norm, nome_norm):
            resultados.append((id_, nome, 90))
            continue

        # Prioridade 4: Fuzzy matching com threshold alto
        score = similaridade(nome_busca, nome)
        if score >= threshold:
            resultados.append((id_, nome, score))

    # Ordena por score decrescente, remove duplicatas
    resultados.sort(key=lambda x: x[2], reverse=True)
    vistos = set()
    unicos = []
    for id_, nome, score in resultados:
        if id_ not in vistos:
            vistos.add(id_)
            unicos.append((id_, nome))

    return unicos


def buscar_funcionario_inteligente(texto_busca, threshold=80):
    if not texto_busca or len(texto_busca.strip()) < 1:
        return [], False, False

    texto_norm = remover_acentos(texto_busca.lower())
    quer_ramal = any(p in texto_norm for p in ["ramal", "telefone", "fone"])
    quer_email = any(p in texto_norm for p in ["email", "e-mail", "mail"])

    # Remove palavras-chave da busca
    nome_limpo = limpar_nome(texto_busca, ["ramal", "email", "e-mail", "telefone", "contato", "do", "da", "de"])
    nome_norm = remover_acentos(nome_limpo.lower()).strip()

    if not nome_norm:
        return [], quer_ramal, quer_email

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.nome, f.ramal, f.email, f.ativo, s.nome
        FROM funcionarios f
        LEFT JOIN setores s ON f.setor_id = s.id
    """)
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    resultados = []
    for row in dados:
        id_, nome, ramal, email, ativo, setor = row
        nome_func_norm = remover_acentos(nome.lower())
        
        # Prioridade 1: Correspondência exata (nome inteiro)
        if nome_norm == nome_func_norm:
            resultados.append((row, 100))
            continue
        
        # Prioridade 2: Palavra inteira no início do nome (ex: busca "Felipe" no "Felipe Mammana")
        palavras_nome = nome_func_norm.split()
        if any(palavra_nome.startswith(nome_norm) for palavra_nome in palavras_nome):
            resultados.append((row, 95))
            continue
        
        # Prioridade 3: Palavra inteira em qualquer posição
        if nome_norm in palavras_nome:
            resultados.append((row, 90))
            continue
        
        # Prioridade 4: Fuzzy matching com threshold alto (mais preciso)
        score = similaridade(nome_norm, nome)
        if score >= threshold:
            resultados.append((row, score))

    resultados.sort(key=lambda x: x[1], reverse=True)
    # Limita a 15 resultados para evitar muitos matches imprecisos
    return [r for r, _ in resultados[:15]], quer_ramal, quer_email


def buscar_setor_inteligente(nome_setor, threshold=70):
    """Busca um setor pelo nome e retorna (id, nome) ou None"""
    if not nome_setor or len(nome_setor.strip()) < 1:
        return None

    nome_norm = remover_acentos(nome_setor.lower())

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome FROM setores")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    resultados = []
    for id_, nome in dados:
        nome_setor_norm = remover_acentos(nome.lower())
        palavras_setor = nome_setor_norm.split()

        # Prioridade 1: Correspondência exata
        if nome_norm == nome_setor_norm:
            return (id_, nome)

        # Prioridade 2: Palavra inteira no início
        if any(palavra.startswith(nome_norm) for palavra in palavras_setor):
            resultados.append(((id_, nome), 95))
            continue

        # Prioridade 3: Fuzzy matching
        score = similaridade(nome_setor, nome)
        if score >= threshold:
            resultados.append(((id_, nome), score))

    if resultados:
        resultados.sort(key=lambda x: x[1], reverse=True)
        return resultados[0][0]

    return None


def listar_funcionarios_por_setor(setor_id):
    """Lista todos os funcionários de um setor específico"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, f.nome, f.ramal, f.email, f.ativo
        FROM funcionarios f
        WHERE f.setor_id = %s
        ORDER BY f.nome
    """, (setor_id,))
    dados = cursor.fetchall()
    cursor.close()
    conn.close()
    return dados


def buscar_cnn_inteligente(nome_busca, threshold=75):
    if not nome_busca or len(nome_busca.strip()) < 1:
        return None

    nome_norm = remover_acentos(nome_busca.lower())

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nome FROM cnn_duplos")
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    resultados = []
    for codigo, nome in dados:
        nome_cnn_norm = remover_acentos(nome.lower())
        palavras_cnn = nome_cnn_norm.split()

        # Prioridade 1: Correspondência exata
        if nome_norm == nome_cnn_norm:
            return (codigo, nome)

        # Prioridade 2: Palavra inteira no início
        if any(palavra.startswith(nome_norm) for palavra in palavras_cnn):
            resultados.append(((codigo, nome), 95))
            continue

        # Prioridade 3: Palavra inteira em qualquer posição
        if nome_norm in palavras_cnn:
            resultados.append(((codigo, nome), 90))
            continue

        # Prioridade 4: Fuzzy matching com threshold alto
        score = similaridade(nome_busca, nome)
        if score >= threshold:
            resultados.append(((codigo, nome), score))

    if resultados:
        resultados.sort(key=lambda x: x[1], reverse=True)
        return resultados[0][0]

    return None


# ==========================================================
# CARD HELPERS
# ==========================================================

def card_medico_unico(medico_id, medico_nome):
    crm = crm_medico(medico_id)
    agenda = agenda_medico(medico_nome)
    regras = regras_medico_por_id(medico_id)

    card = '<div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">'

    # HEADER
    card += '<div style="border-bottom: 2px solid #1e40af; padding-bottom: 12px; margin-bottom: 14px;">'
    card += f'<div style="font-size: 18px; font-weight: 600; color: #1e40af;">🩺 Dr(a). {medico_nome}</div>'
    if crm:
        card += f'<div style="color: #6b7280; font-size: 13px; margin-top: 4px;">CRM: {crm}</div>'
    card += '</div>'

    # AGENDA
    if agenda:
        card += '<div style="margin-bottom: 14px;">'
        card += '<div style="font-weight: 600; color: #059669; font-size: 14px; margin-bottom: 8px;">📅 Agenda</div>'
        for item in agenda:
            try:
                d, h1, h2, t = item
                card += f'''
                    <div style="padding: 8px 12px; margin: 4px 0; background: #f0fdf4; border-left: 3px solid #10b981; border-radius: 4px;">
                        <span style="font-weight: 500; color: #065f46;">{d}</span>
                        <span style="color: #059669; margin: 0 6px;">•</span>
                        <span style="color: #047857;">{h1}-{h2}</span>
                        <span style="color: #6b7280; font-size: 12px; margin-left: 6px;">({t})</span>
                    </div>
                '''
            except (ValueError, TypeError):
                continue
        card += '</div>'

    # REGRAS
    if regras:
        try:
            imc_geral, imc_mama, imc_pos, obs, indicacao = regras
            card += '<div style="margin-bottom: 14px;">'
            card += '<div style="font-weight: 600; color: #dc2626; font-size: 14px; margin-bottom: 8px;">📊 Regras e Requisitos</div>'
            if imc_geral:
                card += f'<div style="padding: 6px 10px; margin: 3px 0; background: #fef3c7; border-radius: 4px; font-size: 13px; color: #92400e;"><strong>IMC geral:</strong> {imc_geral}</div>'
            if imc_mama:
                card += f'<div style="padding: 6px 10px; margin: 3px 0; background: #fef3c7; border-radius: 4px; font-size: 13px; color: #92400e;"><strong>IMC mama redutora:</strong> {imc_mama}</div>'
            if imc_pos:
                card += f'<div style="padding: 6px 10px; margin: 3px 0; background: #fef3c7; border-radius: 4px; font-size: 13px; color: #92400e;"><strong>IMC pós-bariátrica:</strong> {imc_pos}</div>'
            if indicacao:
                card += f'<div style="padding: 6px 10px; margin: 3px 0; background: #fef3c7; border-radius: 4px; font-size: 13px; color: #92400e;"><strong>Indicação cirúrgica:</strong> {indicacao}</div>'
            if obs:
                card += f'<div style="padding: 8px 10px; margin: 6px 0; background: #fee2e2; border-left: 3px solid #dc2626; border-radius: 4px; font-size: 13px; color: #991b1b;"><strong>⚠️ Obs:</strong> {obs}</div>'
            card += '</div>'
        except (ValueError, TypeError):
            pass

    # AÇÕES
    card += '<div style="background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px dashed #cbd5e1;">'
    card += '<div style="font-weight: 600; color: #475569; font-size: 13px; margin-bottom: 8px;">💬 Perguntas adicionais:</div>'
    card += '<div style="font-size: 13px; color: #64748b; line-height: 1.8;">'
    card += '• Digite <strong style="color: #1e40af;">sim</strong> para ver os procedimentos<br>'
    card += '• Digite <strong style="color: #059669;">duplos</strong> para ver procedimentos duplos<br>'
    card += '• Digite <strong style="color: #6b7280;">não</strong> para fazer outra pergunta'
    card += '</div></div>'

    card += '</div>'
    return card


def card_lista_medicos(medicos):
    card = '<div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">'
    card += '<div style="border-bottom: 2px solid #1e40af; padding-bottom: 10px; margin-bottom: 12px;">'
    card += f'<div style="font-size: 16px; font-weight: 600; color: #1e40af;">🩺 {len(medicos)} médico(s) encontrado(s)</div>'
    card += '<div style="font-size: 13px; color: #6b7280; margin-top: 4px;">Digite o nome completo para ver os detalhes:</div>'
    card += '</div>'

    for _, mnome in medicos:
        card += f'''
            <div style="padding: 10px 14px; margin: 6px 0; background: #f0f9ff;
                        border-left: 3px solid #1e40af; border-radius: 6px;
                        font-size: 14px; color: #1e3a5f; font-weight: 500;">
                🩺 Dr(a). {mnome}
            </div>
        '''

    card += '<div style="margin-top: 12px; background: #f8fafc; padding: 10px 12px; border-radius: 8px; border: 1px dashed #cbd5e1;">'
    card += '<div style="font-size: 13px; color: #64748b;">Digite o nome do médico desejado para ver agenda, CRM e regras.</div>'
    card += '</div>'
    card += '</div>'
    return card


def card_nao_encontrado(termo):
    card = '<div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">'
    card += '<div style="font-size: 15px; font-weight: 600; color: #dc2626; margin-bottom: 8px;">❌ Médico não encontrado</div>'
    card += f'<div style="font-size: 13px; color: #6b7280;">Nenhum médico encontrado com o nome <strong>"{termo}"</strong>.</div>'
    card += '<div style="margin-top: 10px; font-size: 13px; color: #64748b;">Verifique o nome e tente novamente.</div>'
    card += '</div>'
    return card


def card_guia_pesquisa():
    card = '<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">'
    
    # HEADER
    card += '<div style="font-size: 22px; font-weight: 700; margin-bottom: 16px;">📖 Guia de Pesquisa</div>'
    card += '<div style="font-size: 13px; opacity: 0.9; margin-bottom: 16px;">Conheça todas as formas de buscar informações no sistema</div>'
    
    # SEÇÕES
    guide = [
        {
            "icon": "🩺",
            "titulo": "BUSCAR MÉDICO",
            "exemplos": ["dr joão silva", "dra maria", "joão", "JS"],
            "resultado": "Mostra agenda, CRM, regras e requisitos"
        },
        {
            "icon": "👤",
            "titulo": "BUSCAR FUNCIONÁRIO",
            "exemplos": ["maria", "ramal 1234", "email sergio", "contato joão"],
            "resultado": "Mostra nome, ramal, email e setor"
        },
        {
            "icon": "🏢",
            "titulo": "BUSCAR SETOR",
            "exemplos": ["tecnologia", "vendas", "rh", "ti", "enfermagem"],
            "resultado": "Lista todos os funcionários do setor com contato"
        },
        {
            "icon": "📋",
            "titulo": "BUSCAR CÓDIGO CNN",
            "exemplos": ["codigo retirada de pele", "qual é o código do", "código da mamoplastia"],
            "resultado": "Retorna o código CNN do procedimento"
        },
        {
            "icon": "✅",
            "titulo": "CONFIRMAR PROCEDIMENTO",
            "exemplos": ["dr joão faz mamoplastia", "dra maria + implante"],
            "resultado": "Confirma se o médico realiza o procedimento"
        },
        {
            "icon": "📊",
            "titulo": "PROCEDIMENTOS DO MÉDICO",
            "exemplos": ["(após buscar o médico) sim"],
            "resultado": "Lista todos os procedimentos do médico"
        },
        {
            "icon": "🔗",
            "titulo": "PROCEDIMENTOS DUPLOS",
            "exemplos": ["(após buscar o médico) duplos"],
            "resultado": "Mostra procedimentos duplos (CNN)"
        }
    ]
    
    for item in guide:
        card += f'''
        <div style="background: rgba(255,255,255,0.1); border-left: 4px solid rgba(255,255,255,0.4); border-radius: 6px; padding: 12px; margin-bottom: 12px;">
            <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px;">
                <span style="font-size: 18px; margin-right: 8px;">{item['icon']}</span>{item['titulo']}
            </div>
            <div style="font-size: 13px; color: rgba(255,255,255,0.9); margin-bottom: 6px;">
                <strong>Exemplos:</strong> {', '.join([f'<em>"{ex}"</em>' for ex in item['exemplos']])}
            </div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.8); padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.2); margin-top: 6px;">
                📌 {item['resultado']}
            </div>
        </div>
        '''
    
    card += '<div style="margin-top: 16px; padding-top: 12px; border-top: 2px solid rgba(255,255,255,0.3);">'
    card += '<div style="font-size: 12px; opacity: 0.85;">💡 <strong>Dica:</strong> Digite <em>"guia"</em> a qualquer momento para ver este menu novamente</div>'
    card += '</div>'
    
    card += '</div>'
    return card


# ==========================================================
# RESPONDER
# ==========================================================

def responder(texto, id_setor=None):
    try:
        print(f"DEBUG SETOR RECEBIDO = {id_setor}")
        print(f"DEBUG TEXTO ORIGINAL = {texto}")
        global estado
        texto = normalizar(texto)
        print(f"DEBUG TEXTO NORMALIZADO = {texto}")

        # ==========================================================
        # GUIA DE PESQUISA
        # ==========================================================
        if texto == "guia" or texto == "ajuda" or texto == "help":
            print("DEBUG: Mostrando guia")
            estado["medico_atual"] = None
            estado["esperando_procedimentos"] = False
            estado["esperando_duplos"] = False
            return card_guia_pesquisa()

        # ==========================================================
        # CONTEXTO (sim / duplos / não)
        # ==========================================================
        if estado["medico_atual"]:
            medico_id, medico_nome = estado["medico_atual"]

            if texto == "sim" and estado["esperando_procedimentos"]:
                procedimentos = procedimentos_do_medico(medico_id)
                estado["esperando_procedimentos"] = False
                if procedimentos:
                    lista_proc = "".join([
                        f'<div style="padding: 8px; margin: 4px 0; background: #f0f9ff; border-left: 3px solid #0ea5e9; border-radius: 4px;">'
                        f'  <span style="color: #0c4a6e;">• {p}</span>'
                        f'</div>'
                        for p in procedimentos
                    ])
                    return f'''
                        <div style="margin: 8px 0;">
                            <div style="font-weight: 600; color: #1e40af; margin-bottom: 8px; font-size: 14px;">
                                🩺 Procedimentos realizados por Dr(a). {medico_nome}
                            </div>
                            {lista_proc}
                        </div>
                    '''
                return '<div style="padding: 12px; background: #fef3c7; border-left: 3px solid #f59e0b; border-radius: 6px; color: #92400e;">ℹ️ Este médico não possui procedimentos cadastrados.</div>'

            if texto == "duplos" and estado["esperando_duplos"]:
                duplos = buscar_duplos_do_medico(medico_id)
                estado["esperando_duplos"] = False
                if duplos:
                    lista_duplos = "".join([
                        f'<div style="padding: 8px; margin: 4px 0; background: #f0fdf4; border-left: 3px solid #10b981; border-radius: 4px;">'
                        f'  <span style="color: #065f46; font-weight: 500;">{nome}</span>'
                        f'  <span style="color: #059669; font-size: 12px; margin-left: 8px;">(CNN {codigo})</span>'
                        f'</div>'
                        for codigo, nome in duplos
                    ])
                    return f'''
                        <div style="margin: 8px 0;">
                            <div style="font-weight: 600; color: #065f46; margin-bottom: 8px; font-size: 14px;">
                                🔗 Procedimentos duplos - Dr(a). {medico_nome}
                            </div>
                            {lista_duplos}
                        </div>
                    '''
                return '<div style="padding: 12px; background: #fef3c7; border-left: 3px solid #f59e0b; border-radius: 6px; color: #92400e;">ℹ️ Este médico não realiza procedimentos duplos.</div>'

            if texto == "não":
                estado["medico_atual"] = None
                estado["esperando_procedimentos"] = False
                estado["esperando_duplos"] = False
                return '<div style="padding: 12px; background: #f0f9ff; border-radius: 8px; color: #0c4a6e; text-align: center;">👍 Tudo bem! Pode perguntar outra coisa 😊</div>'

        # ==========================================================
        # CÓDIGO CNN PELO NOME
        # ==========================================================
        if "codigo" in texto or "código" in texto:
            nome = limpar_nome(texto, ["codigo", "código", "qual é o", "qual", "da", "do"])
            cnn = buscar_cnn_inteligente(nome)
            if cnn:
                codigo, nome_dupla = cnn
                return f'''
                    <div style="padding: 14px; background: linear-gradient(135deg, #e0e7ff 0%, #f0f9ff 100%); border-radius: 8px; border: 1px solid #c7d2fe;">
                        <div style="font-weight: 600; color: #1e40af; font-size: 14px; margin-bottom: 6px;">
                            📋 {nome_dupla}
                        </div>
                        <div style="display: inline-block; padding: 6px 12px; background: #1e40af; color: white; border-radius: 6px; font-size: 13px; font-weight: 500;">
                            Código CNN: {codigo}
                        </div>
                    </div>
                '''
            return '<div style="padding: 12px; background: #fee2e2; border-left: 3px solid #dc2626; border-radius: 6px; color: #991b1b;">❌ Não encontrei esse procedimento duplo.</div>'

        # ==========================================================
        # MÉDICO FAZ PROCEDIMENTO DUPLO?
        # ==========================================================
        if "faz" in texto and "+" in texto:
            partes = texto.split("faz")
            nome_med = limpar_nome(partes[0], ["dr", "dra"])
            nome_dupla = partes[1].strip()

            medicos = buscar_medico_inteligente(nome_med)
            if medicos:
                medico_id, medico_nome = medicos[0]
                resultado = medico_faz_cnn_dupla_por_nome(medico_id, nome_dupla)
                if resultado:
                    codigo, nome_real = resultado
                    return f'''
                        <div style="padding: 14px; background: #f0fdf4; border-left: 4px solid #10b981; border-radius: 8px;">
                            <div style="font-size: 20px; margin-bottom: 8px;">✅</div>
                            <div style="color: #065f46; font-size: 14px; line-height: 1.6;">
                                <strong>Dr(a). {medico_nome}</strong> realiza<br>
                                <strong style="color: #059669;">{nome_real}</strong>
                            </div>
                            <div style="margin-top: 10px; padding: 6px 10px; background: #d1fae5; border-radius: 4px; display: inline-block; font-size: 12px; color: #065f46;">
                                CNN: {codigo}
                            </div>
                        </div>
                    '''
                return f'''
                    <div style="padding: 14px; background: #fef2f2; border-left: 4px solid #dc2626; border-radius: 8px;">
                        <div style="font-size: 20px; margin-bottom: 8px;">❌</div>
                        <div style="color: #991b1b; font-size: 14px; line-height: 1.6;">
                            <strong>Dr(a). {medico_nome}</strong> não realiza<br>
                            <strong>{nome_dupla}</strong>
                        </div>
                    </div>
                '''

        # ==========================================================
        # BUSCA FUNCIONÁRIO (quando não começa com dr)
        # ==========================================================
        if not texto.startswith("dr") and "codigo" not in texto and "código" not in texto and "faz" not in texto:
            texto_func = limpar_nome(texto, ["ramal", "email", "telefone", "contato", "do", "da"])
            
            # Primeiro tenta buscar por setor
            if texto_func and len(texto_func.strip()) >= 2:
                setor_encontrado = buscar_setor_inteligente(texto_func)
                if setor_encontrado:
                    setor_id, setor_nome = setor_encontrado
                    funcionarios_setor = listar_funcionarios_por_setor(setor_id)
                    
                    if funcionarios_setor:
                        resposta = []
                        # Header do setor
                        header = f'<div style="padding: 16px; margin: 8px 0; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 12px; color: white; font-weight: 600; font-size: 16px; text-align: center;">👥 SETOR: {setor_nome}</div>'
                        resposta.append(header)
                        
                        # Funcionários do setor
                        for id_, nome, ramal, email, ativo in funcionarios_setor:
                            status_badge = ""
                            if not ativo:
                                status_badge = '<div style="padding: 6px 10px; background: #fee2e2; border-radius: 6px; color: #991b1b; font-size: 12px; font-weight: 500; margin-bottom: 8px;">⚠️ Inativo</div>'

                            card = '<div style="padding: 14px; margin: 8px 0; background: white; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
                            card += status_badge
                            card += f'<div style="font-weight: 600; color: #1f2937; font-size: 15px; margin-bottom: 8px;">{nome}</div>'

                            info = '<div style="display: flex; flex-direction: column; gap: 6px;">'
                            if ramal:
                                info += f'<div style="display: flex; align-items: center; gap: 8px;"><span style="color: #059669;">📞</span><span style="color: #374151; font-size: 13px;">Ramal: <strong>{ramal}</strong></span></div>'
                            if email:
                                info += f'<div style="display: flex; align-items: center; gap: 8px;"><span style="color: #0ea5e9;">📧</span><span style="color: #374151; font-size: 13px; word-break: break-all;">{email}</span></div>'
                            info += '</div>'

                            card += info
                            card += '</div>'
                            resposta.append(card)

                        return "".join(resposta)
            
            # Se não encontrou setor, tenta buscar por funcionário
            if texto_func and len(texto_func.strip()) >= 2:
                resultados, quer_ramal, quer_email = buscar_funcionario_inteligente(texto_func)
                if resultados:
                    resposta = []
                    for row in resultados:
                        id_, nome, ramal, email, ativo, setor = row
                        status_badge = ""
                        if not ativo:
                            status_badge = '<div style="padding: 6px 10px; background: #fee2e2; border-radius: 6px; color: #991b1b; font-size: 12px; font-weight: 500; margin-bottom: 8px;">⚠️ Não faz mais parte do quadro de funcionários</div>'

                        card = '<div style="padding: 14px; margin: 8px 0; background: white; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
                        card += status_badge
                        card += f'<div style="font-weight: 600; color: #1f2937; font-size: 15px; margin-bottom: 6px;">{nome}</div>'

                        if setor and not (quer_ramal or quer_email):
                            card += f'<div style="color: #6b7280; font-size: 12px; margin-bottom: 8px;">{setor}</div>'

                        info = '<div style="display: flex; flex-direction: column; gap: 6px;">'
                        if quer_ramal or (not quer_email):
                            info += f'<div style="display: flex; align-items: center; gap: 8px;"><span style="color: #059669;">📞</span><span style="color: #374151; font-size: 13px;">Ramal: <strong>{ramal}</strong></span></div>'
                        if quer_email or (not quer_ramal):
                            info += f'<div style="display: flex; align-items: center; gap: 8px;"><span style="color: #0ea5e9;">📧</span><span style="color: #374151; font-size: 13px; word-break: break-all;">{email}</span></div>'
                        info += '</div>'

                        card += info
                        card += '</div>'
                        resposta.append(card)

                    return "".join(resposta)

        # ==========================================================
        # MÉDICO (com ou sem Dr)
        # ==========================================================
        nome_medico = limpar_nome(texto, ["dr", "dra", "consultar", "listar", "todos", "doutor", "doutora"])
        
        if not nome_medico or len(nome_medico.strip()) < 2:
            estado["medico_atual"] = None
            estado["esperando_procedimentos"] = False
            estado["esperando_duplos"] = False
            todos_medicos = buscar_medico_inteligente("", listar_todos=True)
            if todos_medicos:
                return card_lista_medicos(todos_medicos)
            return card_nao_encontrado("médico")
        
        medicos = buscar_medico_inteligente(nome_medico, threshold=70)

        if medicos:
            if len(medicos) == 1:
                medico_id, medico_nome = medicos[0]
                estado["medico_atual"] = (medico_id, medico_nome)
                estado["esperando_procedimentos"] = True
                estado["esperando_duplos"] = True
                return card_medico_unico(medico_id, medico_nome)
            else:
                estado["medico_atual"] = None
                estado["esperando_procedimentos"] = False
                estado["esperando_duplos"] = False
                return card_lista_medicos(medicos)
        
        medicos = buscar_medico_inteligente(nome_medico, threshold=50)
        if medicos:
            estado["medico_atual"] = None
            estado["esperando_procedimentos"] = False
            estado["esperando_duplos"] = False
            return card_lista_medicos(medicos)
        
        estado["medico_atual"] = None
        estado["esperando_procedimentos"] = False
        estado["esperando_duplos"] = False
        
        todos_medicos = buscar_medico_inteligente("", listar_todos=True)
        if todos_medicos:
            card = '<div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">'
            card += '<div style="border-bottom: 2px solid #f59e0b; padding-bottom: 10px; margin-bottom: 12px;">'
            card += '<div style="font-size: 14px; font-weight: 600; color: #d97706;">⚠️ Não encontrei com esse nome...</div>'
            card += '<div style="font-size: 13px; color: #6b7280; margin-top: 4px;">Aqui estão TODOS os médicos cadastrados:</div>'
            card += '</div>'
            for _, mnome in todos_medicos:
                card += f'''
                    <div style="padding: 10px 14px; margin: 6px 0; background: #f0f9ff;
                                border-left: 3px solid #1e40af; border-radius: 6px;
                                font-size: 14px; color: #1e3a5f; font-weight: 500;">
                        🩺 Dr(a). {mnome}
                    </div>
                '''
            card += '<div style="margin-top: 12px; background: #f8fafc; padding: 10px 12px; border-radius: 8px; border: 1px dashed #cbd5e1;">'
            card += '<div style="font-size: 13px; color: #64748b;">Digite o nome do médico desejado para ver agenda, CRM e regras.</div>'
            card += '</div>'
            card += '</div>'
            return card
        
        return card_nao_encontrado(nome_medico or texto)
    
    except Exception as e:
        print(f"ERRO NA FUNÇÃO RESPONDER: {str(e)}")
        import traceback
        traceback.print_exc()
        return f'<div style="padding: 14px; background: #fef2f2; border-left: 4px solid #dc2626; border-radius: 8px;"><div style="color: #991b1b; font-weight: 600;">❌ Erro ao processar</div><div style="color: #991b1b; font-size: 12px; margin-top: 6px;">{str(e)}</div></div>'

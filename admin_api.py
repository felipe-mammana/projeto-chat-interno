from db import get_conn
import bcrypt
from datetime import timedelta


def timedelta_to_str(td):
    """Converte timedelta para string HH:MM"""
    if td is None:
        return None
    if isinstance(td, str):
        return td
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

class AdminAPI:
    # =========================
    # MÉDICOS
    # =========================
    def admin_contar_medicos(self):
        """Conta total e ativos de médicos"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT COUNT(*) AS total FROM medicos")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS ativos FROM medicos WHERE ativo = 1")
        ativos = cur.fetchone()["ativos"]

        conn.close()
        return {"total": total, "ativos": ativos}

    def admin_listar_medicos(self):
        """Lista médicos com informações de regras, procedimentos e agenda"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome, crm, ativo FROM medicos ORDER BY nome")
        medicos = cur.fetchall()

        for medico in medicos:
            medico_id = medico['id']
            
            cur.execute("""
                SELECT COUNT(*) as total
                FROM medico_procedimento
                WHERE medico_id = %s
            """, (medico_id,))
            medico['total_procedimentos'] = cur.fetchone()['total']
            
            cur.execute("""
                SELECT COUNT(*) as total
                FROM agenda_medico
                WHERE medico_id = %s
            """, (medico_id,))
            medico['total_agendas'] = cur.fetchone()['total']
            
            cur.execute("""
                SELECT COUNT(*) as total
                FROM medico_regras
                WHERE medico_id = %s
            """, (medico_id,))
            medico['tem_regras'] = cur.fetchone()['total'] > 0

        conn.close()
        return medicos

    def admin_obter_medico(self, id):
        """Obtém dados completos de um médico"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome, crm, ativo FROM medicos WHERE id = %s", (id,))
        medico = cur.fetchone()
        
        if not medico:
            conn.close()
            return None
            
        conn.close()
        return medico

    def admin_criar_medico(self, nome, crm, ativo):
        """Cria novo médico"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("INSERT INTO medicos (nome, crm, ativo) VALUES (%s, %s, %s)", (nome, crm, ativo))
        conn.commit()
        medico_id = cur.lastrowid
        conn.close()
        return medico_id

    def admin_editar_medico(self, id, nome, crm, ativo):
        """Edita médico existente"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("UPDATE medicos SET nome=%s, crm=%s, ativo=%s WHERE id=%s", (nome, crm, ativo, id))
        conn.commit()
        conn.close()
        return True

    def admin_excluir_medico(self, id):
        """Exclui médico e dados relacionados"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM medico_procedimento WHERE medico_id=%s", (id,))
        cur.execute("DELETE FROM medico_regras WHERE medico_id=%s", (id,))
        cur.execute("DELETE FROM agenda_atendimento WHERE agenda_id IN (SELECT id FROM agenda_medico WHERE medico_id=%s)", (id,))
        cur.execute("DELETE FROM agenda_medico WHERE medico_id=%s", (id,))
        cur.execute("DELETE FROM medicos WHERE id=%s", (id,))
        
        conn.commit()
        conn.close()
        return True

    # =========================
    # REGRAS DO MÉDICO
    # =========================
    def admin_obter_medico_regras(self, medico_id):
        """Obtém regras de um médico"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT imc_geral, imc_mama_redutora, imc_pos_bariatrica,
                   max_cirurgias_combinadas, indicacao_cirurgica, observacoes
            FROM medico_regras
            WHERE medico_id = %s
        """, (medico_id,))
        
        regras = cur.fetchone()
        conn.close()
        
        if not regras:
            return {
                'imc_geral': '',
                'imc_mama_redutora': '',
                'imc_pos_bariatrica': '',
                'max_cirurgias_combinadas': '',
                'indicacao_cirurgica': 0,
                'observacoes': ''
            }
        
        return {
            'imc_geral': float(regras['imc_geral']) if regras['imc_geral'] else '',
            'imc_mama_redutora': float(regras['imc_mama_redutora']) if regras['imc_mama_redutora'] else '',
            'imc_pos_bariatrica': float(regras['imc_pos_bariatrica']) if regras['imc_pos_bariatrica'] else '',
            'max_cirurgias_combinadas': int(regras['max_cirurgias_combinadas']) if regras['max_cirurgias_combinadas'] else '',
            'indicacao_cirurgica': int(regras['indicacao_cirurgica']) if regras['indicacao_cirurgica'] else 0,
            'observacoes': regras['observacoes'] or ''
        }

    def admin_salvar_medico_regras(self, medico_id, imc_geral, imc_mama_redutora, 
                                     imc_pos_bariatrica, max_cirurgias_combinadas, 
                                     indicacao_cirurgica, observacoes):
        """Salva ou atualiza regras de um médico"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT id FROM medico_regras WHERE medico_id = %s", (medico_id,))
        existe = cur.fetchone()

        imc_geral = float(imc_geral) if imc_geral else None
        imc_mama_redutora = float(imc_mama_redutora) if imc_mama_redutora else None
        imc_pos_bariatrica = float(imc_pos_bariatrica) if imc_pos_bariatrica else None
        max_cirurgias = int(max_cirurgias_combinadas) if max_cirurgias_combinadas else None
        indicacao = 1 if indicacao_cirurgica else 0

        if existe:
            cur.execute("""
                UPDATE medico_regras
                SET imc_geral=%s, imc_mama_redutora=%s, imc_pos_bariatrica=%s,
                    max_cirurgias_combinadas=%s, indicacao_cirurgica=%s, observacoes=%s
                WHERE medico_id=%s
            """, (imc_geral, imc_mama_redutora, imc_pos_bariatrica, max_cirurgias, 
                  indicacao, observacoes, medico_id))
        else:
            cur.execute("""
                INSERT INTO medico_regras 
                (medico_id, imc_geral, imc_mama_redutora, imc_pos_bariatrica,
                 max_cirurgias_combinadas, indicacao_cirurgica, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (medico_id, imc_geral, imc_mama_redutora, imc_pos_bariatrica,
                  max_cirurgias, indicacao, observacoes))

        conn.commit()
        conn.close()
        return True

    # =========================
    # PROCEDIMENTOS DO MÉDICO
    # =========================
    def admin_obter_medico_procedimentos(self, medico_id):
        """Obtém procedimentos de um médico"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT p.id, p.nome
            FROM procedimentos p
            INNER JOIN medico_procedimento mp ON mp.procedimento_id = p.id
            WHERE mp.medico_id = %s
            ORDER BY p.nome
        """, (medico_id,))
        
        procedimentos = cur.fetchall()
        conn.close()
        return procedimentos

    def admin_salvar_medico_procedimentos(self, medico_id, procedimentos):
        """Salva procedimentos de um médico"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM medico_procedimento WHERE medico_id = %s", (medico_id,))

        if procedimentos:
            for proc_id in procedimentos:
                cur.execute(
                    "INSERT INTO medico_procedimento (medico_id, procedimento_id) VALUES (%s, %s)",
                    (medico_id, proc_id)
                )

        conn.commit()
        conn.close()
        return True

    # =========================
    # AGENDA DO MÉDICO
    # =========================
    def admin_listar_agenda_medico(self, medico_id=None):
        """Lista agenda médica"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        if medico_id:
            cur.execute("""
                SELECT id, medico_id, dia_semana, hora_inicio, hora_fim
                FROM agenda_medico
                WHERE medico_id = %s
                ORDER BY 
                    FIELD(dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'),
                    hora_inicio
            """, (medico_id,))
        else:
            cur.execute("""
                SELECT id, medico_id, dia_semana, hora_inicio, hora_fim
                FROM agenda_medico
                ORDER BY medico_id, 
                    FIELD(dia_semana, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'),
                    hora_inicio
            """)

        agendas = cur.fetchall()

        for agenda in agendas:
            agenda['hora_inicio'] = timedelta_to_str(agenda['hora_inicio'])
            agenda['hora_fim'] = timedelta_to_str(agenda['hora_fim'])
            
            cur.execute("""
                SELECT ta.id, ta.nome
                FROM tipos_atendimento ta
                INNER JOIN agenda_atendimento aa ON aa.atendimento_id = ta.id
                WHERE aa.agenda_id = %s
            """, (agenda['id'],))
            
            agenda['atendimentos'] = cur.fetchall()

        conn.close()
        return agendas

    def admin_obter_agenda_medico(self, id):
        """Obtém dados de uma agenda"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, medico_id, dia_semana, hora_inicio, hora_fim
            FROM agenda_medico
            WHERE id = %s
        """, (id,))
        
        agenda = cur.fetchone()
        
        if not agenda:
            conn.close()
            return None

        agenda['hora_inicio'] = timedelta_to_str(agenda['hora_inicio'])
        agenda['hora_fim'] = timedelta_to_str(agenda['hora_fim'])

        cur.execute("""
            SELECT atendimento_id
            FROM agenda_atendimento
            WHERE agenda_id = %s
        """, (id,))
        
        agenda['atendimentos'] = [row['atendimento_id'] for row in cur.fetchall()]
        
        conn.close()
        return agenda

    def admin_criar_agenda_medico(self, medico_id, dia_semana, hora_inicio, hora_fim, atendimentos):
        """Cria nova agenda"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO agenda_medico (medico_id, dia_semana, hora_inicio, hora_fim)
            VALUES (%s, %s, %s, %s)
        """, (medico_id, dia_semana, hora_inicio, hora_fim))
        
        agenda_id = cur.lastrowid

        if atendimentos:
            for tipo_id in atendimentos:
                cur.execute("""
                    INSERT INTO agenda_atendimento (agenda_id, atendimento_id)
                    VALUES (%s, %s)
                """, (agenda_id, tipo_id))

        conn.commit()
        conn.close()
        return agenda_id

    def admin_editar_agenda_medico(self, id, medico_id, dia_semana, hora_inicio, hora_fim, atendimentos):
        """Edita agenda existente"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE agenda_medico
            SET medico_id=%s, dia_semana=%s, hora_inicio=%s, hora_fim=%s
            WHERE id=%s
        """, (medico_id, dia_semana, hora_inicio, hora_fim, id))

        cur.execute("DELETE FROM agenda_atendimento WHERE agenda_id=%s", (id,))
        
        if atendimentos:
            for tipo_id in atendimentos:
                cur.execute("""
                    INSERT INTO agenda_atendimento (agenda_id, atendimento_id)
                    VALUES (%s, %s)
                """, (id, tipo_id))

        conn.commit()
        conn.close()
        return True

    def admin_excluir_agenda_medico(self, id):
        """Exclui agenda"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM agenda_atendimento WHERE agenda_id=%s", (id,))
        cur.execute("DELETE FROM agenda_medico WHERE id=%s", (id,))
        
        conn.commit()
        conn.close()
        return True

    # =========================
    # FUNCIONÁRIOS (COM LOGIN INTEGRADO)
    # =========================
    def admin_listar_funcionarios(self):
        """Lista funcionários com indicação se têm login"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT f.id, f.nome, f.email, f.ramal, f.setor_id, f.ativo,
                   s.nome as setor,
                   (SELECT COUNT(*) FROM logins l WHERE l.funcionario_id = f.id) as tem_login
            FROM funcionarios f
            LEFT JOIN setores s ON s.id = f.setor_id
            ORDER BY f.nome
        """)
        
        funcionarios = cur.fetchall()
        
        # Converter tem_login para boolean
        for func in funcionarios:
            func['tem_login'] = func['tem_login'] > 0
        
        conn.close()
        return funcionarios

    def admin_obter_funcionario(self, id):
        """Obtém dados de um funcionário"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, nome, email, ramal, setor_id, ativo
            FROM funcionarios
            WHERE id = %s
        """, (id,))
        
        funcionario = cur.fetchone()
        conn.close()
        return funcionario

    def admin_criar_funcionario(self, nome, email, ramal, setor_id, ativo):
        """Cria novo funcionário"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO funcionarios (nome, email, ramal, setor_id, ativo)
            VALUES (%s, %s, %s, %s, %s)
        """, (nome, email, ramal, setor_id, ativo))
        
        conn.commit()
        func_id = cur.lastrowid
        conn.close()
        return func_id

    def admin_editar_funcionario(self, id, nome, email, ramal, setor_id, ativo):
        """Edita funcionário"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE funcionarios
            SET nome=%s, email=%s, ramal=%s, setor_id=%s, ativo=%s
            WHERE id=%s
        """, (nome, email, ramal, setor_id, ativo, id))
        
        conn.commit()
        conn.close()
        return True

    def admin_excluir_funcionario(self, id):
        """Exclui funcionário e login associado"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM logins WHERE funcionario_id=%s", (id,))
        cur.execute("DELETE FROM funcionarios WHERE id=%s", (id,))
        
        conn.commit()
        conn.close()
        return True

    # =========================
    # SETORES
    # =========================
    def admin_listar_setores(self):
        """Lista setores"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT s.id, s.nome,
                   COUNT(f.id) as total_funcionarios
            FROM setores s
            LEFT JOIN funcionarios f ON f.setor_id = s.id
            GROUP BY s.id, s.nome
            ORDER BY s.nome
        """)
        
        setores = cur.fetchall()
        conn.close()
        return setores

    def admin_obter_setor(self, id):
        """Obtém dados de um setor"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome FROM setores WHERE id = %s", (id,))
        setor = cur.fetchone()
        conn.close()
        return setor

    def admin_criar_setor(self, nome):
        """Cria novo setor"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("INSERT INTO setores (nome) VALUES (%s)", (nome,))
        conn.commit()
        setor_id = cur.lastrowid
        conn.close()
        return setor_id

    def admin_editar_setor(self, id, nome):
        """Edita setor"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("UPDATE setores SET nome=%s WHERE id=%s", (nome, id))
        conn.commit()
        conn.close()
        return True

    def admin_excluir_setor(self, id):
        """Exclui setor"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM setores WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        return True

    # =========================
    # PROCEDIMENTOS
    # =========================
    def admin_listar_procedimentos(self):
        """Lista procedimentos"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome FROM procedimentos ORDER BY nome")
        procedimentos = cur.fetchall()
        conn.close()
        return procedimentos

    def admin_obter_procedimento(self, id):
        """Obtém dados de um procedimento"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome FROM procedimentos WHERE id = %s", (id,))
        procedimento = cur.fetchone()
        conn.close()
        return procedimento

    def admin_criar_procedimento(self, nome):
        """Cria novo procedimento"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("INSERT INTO procedimentos (nome) VALUES (%s)", (nome,))
        conn.commit()
        proc_id = cur.lastrowid
        conn.close()
        return proc_id

    def admin_editar_procedimento(self, id, nome):
        """Edita procedimento"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("UPDATE procedimentos SET nome=%s WHERE id=%s", (nome, id))
        conn.commit()
        conn.close()
        return True

    def admin_excluir_procedimento(self, id):
        """Exclui procedimento"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM medico_procedimento WHERE procedimento_id=%s", (id,))
        cur.execute("DELETE FROM cnn_dupla_procedimento WHERE procedimento_id=%s", (id,))
        cur.execute("DELETE FROM procedimentos WHERE id=%s", (id,))
        
        conn.commit()
        conn.close()
        return True

    # =========================
    # CNN DUPLAS
    # =========================
    def admin_listar_cnn_duplas(self):
        """Lista CNN duplas"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, codigo_cnn, nome FROM cnn_dupla ORDER BY codigo_cnn")
        duplas = cur.fetchall()
        conn.close()
        return duplas

    def admin_obter_cnn_dupla(self, id):
        """Obtém dados de uma CNN dupla"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, codigo_cnn, nome
            FROM cnn_dupla
            WHERE id = %s
        """, (id,))
        
        dupla = cur.fetchone()
        
        if not dupla:
            conn.close()
            return None

        cur.execute("""
            SELECT p.id, p.nome
            FROM procedimentos p
            INNER JOIN cnn_dupla_procedimento cdp ON cdp.procedimento_id = p.id
            WHERE cdp.cnn_dupla_id = %s
        """, (id,))
        
        dupla['procedimentos'] = cur.fetchall()
        conn.close()
        return dupla

    def admin_criar_cnn_dupla(self, codigo_cnn, nome, procedimentos):
        """Cria nova CNN dupla"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO cnn_dupla (codigo_cnn, nome)
            VALUES (%s, %s)
        """, (codigo_cnn, nome))
        
        dupla_id = cur.lastrowid

        if procedimentos:
            for proc_id in procedimentos:
                cur.execute("""
                    INSERT INTO cnn_dupla_procedimento (cnn_dupla_id, procedimento_id)
                    VALUES (%s, %s)
                """, (dupla_id, proc_id))

        conn.commit()
        conn.close()
        return dupla_id

    def admin_editar_cnn_dupla(self, id, codigo_cnn, nome, procedimentos):
        """Edita CNN dupla"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE cnn_dupla
            SET codigo_cnn=%s, nome=%s
            WHERE id=%s
        """, (codigo_cnn, nome, id))

        cur.execute("DELETE FROM cnn_dupla_procedimento WHERE cnn_dupla_id=%s", (id,))
        
        if procedimentos:
            for proc_id in procedimentos:
                cur.execute("""
                    INSERT INTO cnn_dupla_procedimento (cnn_dupla_id, procedimento_id)
                    VALUES (%s, %s)
                """, (id, proc_id))

        conn.commit()
        conn.close()
        return True

    def admin_excluir_cnn_dupla(self, id):
        """Exclui CNN dupla"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM cnn_dupla_procedimento WHERE cnn_dupla_id=%s", (id,))
        cur.execute("DELETE FROM cnn_dupla WHERE id=%s", (id,))
        
        conn.commit()
        conn.close()
        return True

    # =========================
    # TIPOS DE ATENDIMENTO
    # =========================
    def admin_listar_tipos_atendimento(self):
        """Lista tipos de atendimento"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome FROM tipos_atendimento ORDER BY nome")
        tipos = cur.fetchall()
        conn.close()
        return tipos

    def admin_obter_tipo_atendimento(self, id):
        """Obtém dados de um tipo de atendimento"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id, nome FROM tipos_atendimento WHERE id = %s", (id,))
        tipo = cur.fetchone()
        conn.close()
        return tipo

    def admin_criar_tipo_atendimento(self, nome):
        """Cria novo tipo de atendimento"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("INSERT INTO tipos_atendimento (nome) VALUES (%s)", (nome,))
        conn.commit()
        tipo_id = cur.lastrowid
        conn.close()
        return tipo_id

    def admin_editar_tipo_atendimento(self, id, nome):
        """Edita tipo de atendimento"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("UPDATE tipos_atendimento SET nome=%s WHERE id=%s", (nome, id))
        conn.commit()
        conn.close()
        return True

    def admin_excluir_tipo_atendimento(self, id):
        """Exclui tipo de atendimento"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM agenda_atendimento WHERE atendimento_id=%s", (id,))
        cur.execute("DELETE FROM tipos_atendimento WHERE id=%s", (id,))
        
        conn.commit()
        conn.close()
        return True

    # =========================
    # LOGINS (FUNÇÕES AUXILIARES)
    # =========================
    def admin_obter_login_por_funcionario(self, funcionario_id):
        """Obtém login de um funcionário específico"""
        conn = get_conn()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, funcionario_id, usuario, nivel, ativo
            FROM logins
            WHERE funcionario_id = %s
        """, (funcionario_id,))
        
        login = cur.fetchone()
        conn.close()
        
        if not login:
            raise Exception("Login não encontrado")
        
        return login

    def admin_criar_login(self, funcionario_id, usuario, senha, nivel, ativo):
        conn = get_conn()
        cur = conn.cursor()

        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

        cur.execute("""
        INSERT INTO logins (funcionario_id, usuario, senha, nivel, ativo)
        VALUES (%s, %s, %s, %s, %s)
    """, (funcionario_id, usuario, senha_hash, nivel, ativo))

        conn.commit()
        login_id = cur.lastrowid
        conn.close()
        return login_id

    def admin_editar_login(self, id, funcionario_id, usuario, senha, nivel, ativo):
        conn = get_conn()
        cur = conn.cursor()

        if senha:
            senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
            cur.execute("""
                UPDATE logins
                SET funcionario_id=%s, usuario=%s, senha=%s, nivel=%s, ativo=%s
                WHERE id=%s
            """, (funcionario_id, usuario, senha_hash, nivel, ativo, id))
        else:
            cur.execute("""
                UPDATE logins
                SET funcionario_id=%s, usuario=%s, nivel=%s, ativo=%s
                WHERE id=%s
            """, (funcionario_id, usuario, nivel, ativo, id))

        conn.commit()
        conn.close()
        return True

    def admin_excluir_login(self, id):
        """Exclui login"""
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM logins WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        return True
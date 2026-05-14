import re

def normalizar(texto):
    return texto.lower().strip()


def detectar_intencao(texto):
    texto = normalizar(texto)

    if any(p in texto for p in ["ramal", "email", "telefone"]):
        return "funcionario"

    if any(p in texto for p in ["agenda", "atende", "horário", "horario", "quando"]):
        return "agenda_medico"

    if any(p in texto for p in ["imc", "cirurgia tripla", "cirurgia dupla", "quantas cirurgias"]):
        return "regras_medico"

    if any(p in texto for p in ["faz", "realiza", "executa"]):
        return "medico_procedimento"

    return "desconhecido"


def extrair_medico(texto):
    texto = normalizar(texto)
    texto = re.sub(r"(dr\.?|dra\.?)", "", texto)
    return texto


def extrair_funcionario(texto):
    texto = normalizar(texto)
    texto = re.sub(r"(ramal|email|telefone|da|do|de)", "", texto)
    return texto.strip()
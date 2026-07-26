import unicodedata

def remover_acentos(text: str) -> str:
    """
    Remove todos os acentos e diacríticos de uma string.
    Exemplo: 'SG CALAÇA' -> 'SG CALACA'
    """
    if not text:
        return ""
    # Normaliza para a forma NFKD para separar os caracteres base dos acentos
    nfkd = unicodedata.normalize('NFKD', text)
    # Filtra e reconstrói a string removendo os diacríticos combinados (combining)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def normalize_username_slug(text: str) -> str:
    """
    Gera um slug de nome de usuário sem acentos, com pontos no lugar de espaços.
    Exemplo: 'SG CALAÇA' -> 'sg.calaca'
    """
    if not text:
        return ""
    # Remove acentos, passa para minúsculas, limpa espaços nas bordas e substitui espaços por pontos
    cleaned = remover_acentos(text).lower().strip()
    return cleaned.replace(' ', '.')

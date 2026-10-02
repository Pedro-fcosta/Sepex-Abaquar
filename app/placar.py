"""Dados públicos do placar, sem alterar a classificação usada pelo restante do app."""

from datetime import datetime, timezone

from .estatisticas import ranking


def dados_placar():
    # ranking() já aplica apogeu, velocidade, horário e id como desempates.
    # A numeração oficial é feita na interface após retirar as demonstrações.
    linhas = ranking()
    return {
        'gerado_em': datetime.now(timezone.utc).isoformat(),
        'linhas': [
            {
                'id': linha['id'],
                'participante_id': linha['participante_id'],
                'nome': linha['nome'],
                'configuracao_codigo': linha['configuracao_codigo'],
                'apogeu_m': linha['apogeu_m'],
                'velocidade_max_ms': linha['velocidade_max_ms'],
                'horario': linha['horario'],
                'demonstrativo': bool(linha['demonstrativo']),
            }
            for linha in linhas
        ],
    }

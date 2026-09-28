import re
import sqlite3
import unicodedata
from .db import conexao
from .estatisticas import ranking


def registrar(nome, codigo, sessao):
    nome = ' '.join(str(nome or '').split())
    if not 2 <= len(nome) <= 60 or any(ord(c)<32 for c in nome):
        raise ValueError('Informe um nome ou apelido de 2 a 60 caracteres')
    if not re.fullmatch(r'[A-Za-z0-9_-]{12,80}',str(sessao or '')):
        raise ValueError('Identificador da participação inválido')
    db = conexao()
    existente = db.execute('SELECT id FROM tentativas WHERE identificador_sessao=?',(sessao,)).fetchone()
    if existente:
        return existente['id'],False
    config = db.execute('SELECT 1 FROM configuracoes WHERE codigo=? AND ativo=1',(codigo,)).fetchone()
    if not config:
        raise ValueError('Configuração inválida')
    sim = db.execute("SELECT * FROM simulacoes WHERE configuracao_codigo=? AND status='approved' ORDER BY id DESC LIMIT 1",(codigo,)).fetchone()
    if not sim:
        raise ValueError('Configuração sem simulação aprovada')
    normalizado = unicodedata.normalize('NFKC',nome).casefold()
    try:
        with db:
            db.execute('INSERT OR IGNORE INTO participantes(nome,nome_normalizado) VALUES (?,?)',(nome,normalizado))
            participante = db.execute('SELECT id FROM participantes WHERE nome_normalizado=?',(normalizado,)).fetchone()['id']
            cursor = db.execute('''INSERT INTO tentativas(participante_id,configuracao_codigo,simulacao_id,apogeu_m,
                velocidade_max_ms,aceleracao_max_ms2,margem_calibres,identificador_sessao,demonstrativo)
                VALUES (?,?,?,?,?,?,?,?,?)''',(participante,codigo,sim['id'],sim['apogeu_m'],sim['velocidade_max_ms'],sim['aceleracao_max_ms2'],sim['margem_calibres'],sessao,sim['demonstrativo']))
            id_tentativa = cursor.lastrowid
            posicao = next(r['posicao'] for r in ranking() if r['id']==id_tentativa)
            db.execute('UPDATE tentativas SET posicao_calculada=? WHERE id=?',(posicao,id_tentativa))
    except sqlite3.IntegrityError:
        repetida = db.execute('SELECT id FROM tentativas WHERE identificador_sessao=?',(sessao,)).fetchone()
        if not repetida:
            raise
        return repetida['id'],False
    return id_tentativa,True

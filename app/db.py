import sqlite3
from flask import current_app, g

ESQUEMA = '''
CREATE TABLE IF NOT EXISTS componentes (
 id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, categoria TEXT NOT NULL,
 nome TEXT NOT NULL, descricao TEXT, imagem TEXT, propriedades_json TEXT NOT NULL DEFAULT '{}', ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS configuracoes (
 codigo TEXT PRIMARY KEY, coifa TEXT NOT NULL REFERENCES componentes(codigo),
 aleta TEXT NOT NULL REFERENCES componentes(codigo), quantidade_aletas INTEGER NOT NULL,
 secoes INTEGER NOT NULL, comprimento_corpo_mm INTEGER NOT NULL, ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS condicoes (
 id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE, motor TEXT, temperatura_c REAL,
 pressao_pa REAL, vento_ms REAL, direcao_vento_graus REAL, altitude_local_m REAL,
 trilho TEXT, versao_openrocket TEXT, observacoes TEXT, data_simulacao TEXT,
 revisao_tecnica TEXT NOT NULL DEFAULT 'pending_review'
);
CREATE TABLE IF NOT EXISTS simulacoes (
 id INTEGER PRIMARY KEY, configuracao_codigo TEXT NOT NULL REFERENCES configuracoes(codigo),
 condicao_id INTEGER REFERENCES condicoes(id), apogeu_m REAL NOT NULL, velocidade_max_ms REAL,
 aceleracao_max_ms2 REAL, tempo_apogeu_s REAL, duracao_s REAL, cg_m REAL, cp_m REAL,
 margem_calibres REAL, aviso_estabilidade TEXT, unidades_originais_json TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL DEFAULT 'pending_review' CHECK(status IN ('pending_review','approved','rejected')),
 origem TEXT NOT NULL, hash_arquivo TEXT NOT NULL, importado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 observacoes TEXT, demonstrativo INTEGER NOT NULL DEFAULT 0,
 UNIQUE(configuracao_codigo, hash_arquivo)
);
CREATE TABLE IF NOT EXISTS pontos (
 id INTEGER PRIMARY KEY, simulacao_id INTEGER NOT NULL REFERENCES simulacoes(id) ON DELETE CASCADE,
 tempo_s REAL NOT NULL, altitude_m REAL NOT NULL, velocidade_ms REAL, aceleracao_ms2 REAL,
 UNIQUE(simulacao_id, tempo_s)
);
CREATE TABLE IF NOT EXISTS participantes (
 id INTEGER PRIMARY KEY, nome TEXT NOT NULL, nome_normalizado TEXT NOT NULL UNIQUE,
 criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tentativas (
 id INTEGER PRIMARY KEY, participante_id INTEGER NOT NULL REFERENCES participantes(id),
 configuracao_codigo TEXT NOT NULL REFERENCES configuracoes(codigo),
 simulacao_id INTEGER NOT NULL REFERENCES simulacoes(id), horario TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 apogeu_m REAL NOT NULL, velocidade_max_ms REAL, aceleracao_max_ms2 REAL, margem_calibres REAL,
 posicao_calculada INTEGER, identificador_sessao TEXT NOT NULL UNIQUE, demonstrativo INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_simulacoes_config_status ON simulacoes(configuracao_codigo,status);
CREATE INDEX IF NOT EXISTS idx_tentativas_ranking ON tentativas(apogeu_m DESC,velocidade_max_ms DESC,horario ASC);
'''


def conexao():
    if 'db' not in g:
        db = sqlite3.connect(current_app.config['DATABASE'], timeout=20)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA busy_timeout=20000')
        g.db = db
    return g.db


def fechar_conexao(_erro=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def inicializar():
    conexao().executescript(ESQUEMA)
    conexao().commit()

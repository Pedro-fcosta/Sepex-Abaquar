from app.db import conexao


def inserir_tentativa(app, nome, codigo, apogeu, velocidade, horario, demonstrativo=False):
    with app.app_context():
        db = conexao()
        with db:
            db.execute('INSERT OR IGNORE INTO participantes(nome,nome_normalizado) VALUES (?,?)', (nome, nome.casefold()))
            participante_id = db.execute('SELECT id FROM participantes WHERE nome_normalizado=?', (nome.casefold(),)).fetchone()['id']
            simulacao = db.execute('''INSERT INTO simulacoes(configuracao_codigo,apogeu_m,velocidade_max_ms,origem,hash_arquivo,status,demonstrativo)
                VALUES (?,?,?,?,?,?,?)''', (codigo, apogeu, velocidade, 'DEMO' if demonstrativo else 'OpenRocket', f'placar-{nome}-{horario}', 'approved', int(demonstrativo)))
            tentativa = db.execute('''INSERT INTO tentativas(participante_id,configuracao_codigo,simulacao_id,horario,
                apogeu_m,velocidade_max_ms,identificador_sessao,demonstrativo) VALUES (?,?,?,?,?,?,?,?)''',
                (participante_id, codigo, simulacao.lastrowid, horario, apogeu, velocidade,
                 f'placar-{nome}-{horario}', int(demonstrativo)))
        return tentativa.lastrowid


def test_placar_vazio_e_modo_telao(cliente):
    resposta = cliente.get('/api/ranking/placar')
    assert resposta.status_code == 200
    assert resposta.json['linhas'] == []
    assert resposta.headers['Cache-Control'] == 'no-store'
    pagina = cliente.get('/ranking?display=1')
    assert pagina.status_code == 200
    assert b'ranking-telao' in pagina.data
    assert b'ranking-dados-iniciais' in pagina.data


def test_placar_publico_preserva_desempate_e_marca_demo(app, cliente):
    codigo = 'C1-A1-F3-S1'
    antigo = inserir_tentativa(app, 'Ana', codigo, 120, 50, '2026-09-28 09:00:00')
    recente = inserir_tentativa(app, 'Bia', codigo, 120, 50, '2026-09-28 10:00:00')
    rapido = inserir_tentativa(app, 'Caio', codigo, 120, 55, '2026-09-28 11:00:00')
    demo = inserir_tentativa(app, 'Ana', codigo, 300, 90, '2026-09-28 12:00:00', True)
    linhas = cliente.get('/api/ranking/placar').json['linhas']
    assert [linha['id'] for linha in linhas] == [demo, rapido, antigo, recente]
    assert [linha['demonstrativo'] for linha in linhas] == [True, False, False, False]
    assert all('identificador_sessao' not in linha for linha in linhas)
    assert cliente.get('/api/ranking').status_code == 200
    assert cliente.get('/ranking?melhor=1').status_code == 200

from pathlib import Path

import pytest

from app.db import conexao
from app.simulacoes import importar, ler_csv


LOTE = Path(__file__).resolve().parents[1] / 'Foguete Modular - Banco' / '.csv'


def test_pouso_abaixo_de_zero_apenas_no_ultimo_ponto():
    base = b'Time (s),Altitude (m)\n0,0\n1,10\n2,'
    resumo, pontos, _ = ler_csv(base + b'-0.2\n')
    assert resumo['apogeu'] == 10
    assert pontos[-1]['altitude'] == 0
    with pytest.raises(ValueError, match='Altitude negativa'):
        ler_csv(b'Time (s),Altitude (m)\n0,0\n1,-0.2\n2,10\n')
    with pytest.raises(ValueError, match='Altitude negativa'):
        ler_csv(base + b'-2\n')


def test_lote_importado_libera_todos_os_voos_e_graficos(app, cliente):
    comando = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert comando.exit_code == 0, comando.output
    assert '21 importadas' in comando.output
    repetido = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert repetido.exit_code == 0, repetido.output
    assert '21 já existentes' in repetido.output
    with app.app_context():
        db = conexao()
        assert db.execute("SELECT count(*) FROM simulacoes WHERE status='approved'").fetchone()[0] == 21
        assert db.execute('SELECT count(*) FROM pontos').fetchone()[0] > 10_000
        assert db.execute('SELECT count(*) FROM tentativas').fetchone()[0] == 0
        assert 'No recovery device' in db.execute("SELECT observacoes FROM simulacoes WHERE configuracao_codigo='C1-A1-F3-S1'").fetchone()[0]
    estado = cliente.get('/api/configuracoes/C1-A1-F3-S1').json
    assert estado['disponivel'] is True
    assert estado['url_previa'] == '/previa/C1-A1-F3-S1'
    assert cliente.get(estado['url_previa']).status_code == 200
    dados = cliente.get('/api/previa/C1-A1-F3-S1').json
    assert dados['previa'] is True
    assert dados['origem_trajetoria'] == 'serie_openrocket'
    assert len(dados['pontos']) > 900
    assert dados['pontos'][-1]['altitude_m'] == 0
    assert 'termina antes do pouso' in cliente.get('/previa/C2-A3-F3-S1').get_data(as_text=True)
    with app.app_context():
        assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0] == 0
    for arquivo in sorted(LOTE.rglob('*.csv')):
        codigo = arquivo.stem
        resposta = cliente.post('/api/tentativas', json={
            'nome': f'Teste {codigo}', 'codigo': codigo, 'identificador_sessao': f'teste-{codigo}'
        })
        assert resposta.status_code == 201, (codigo, resposta.json)
        voo = cliente.get(resposta.json['url_voo'])
        assert voo.status_code == 200
        serie = cliente.get(f'/api/voo/{resposta.json["id"]}').json
        assert len(serie['pontos']) > 1
        assert serie['origem_trajetoria'] == 'serie_openrocket'
    with app.app_context():
        assert conexao().execute('SELECT count(*) FROM tentativas').fetchone()[0] == 21


def test_reimportacao_ativa_lote_que_ja_estava_pendente(app):
    arquivo = next(LOTE.rglob('*.csv'))
    with app.app_context():
        identificador, _ = importar(arquivo.read_bytes(), arquivo.name, arquivo.stem, ativar=False)
        assert conexao().execute('SELECT status FROM simulacoes WHERE id=?', (identificador,)).fetchone()[0] == 'pending_review'
    resultado = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert resultado.exit_code == 0, resultado.output
    with app.app_context():
        assert conexao().execute("SELECT count(*) FROM simulacoes WHERE status='approved'").fetchone()[0] == 21

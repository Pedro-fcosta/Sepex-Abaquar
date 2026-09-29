from pathlib import Path

import pytest

from app.db import conexao
from app.simulacoes import ler_csv


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


def test_lote_importado_permite_previa_sem_liberar_ranking(app, cliente):
    comando = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert comando.exit_code == 0, comando.output
    assert '21 importadas' in comando.output
    repetido = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert repetido.exit_code == 0, repetido.output
    assert '21 já existentes' in repetido.output
    with app.app_context():
        db = conexao()
        assert db.execute("SELECT count(*) FROM simulacoes WHERE status='pending_review'").fetchone()[0] == 21
        assert db.execute('SELECT count(*) FROM pontos').fetchone()[0] > 10_000
        assert db.execute('SELECT count(*) FROM tentativas').fetchone()[0] == 0
        assert 'No recovery device' in db.execute("SELECT observacoes FROM simulacoes WHERE configuracao_codigo='C1-A1-F3-S1'").fetchone()[0]
    estado = cliente.get('/api/configuracoes/C1-A1-F3-S1').json
    assert estado['disponivel'] is False
    assert estado['url_previa'] == '/previa/C1-A1-F3-S1'
    assert cliente.get(estado['url_previa']).status_code == 200
    dados = cliente.get('/api/previa/C1-A1-F3-S1').json
    assert dados['previa'] is True
    assert dados['origem_trajetoria'] == 'serie_openrocket'
    assert len(dados['pontos']) > 900
    assert dados['pontos'][-1]['altitude_m'] == 0
    assert 'termina antes do pouso' in cliente.get('/previa/C2-A3-F3-S1').get_data(as_text=True)
    assert cliente.post('/api/tentativas', json={
        'nome': 'Teste', 'codigo': 'C1-A1-F3-S1', 'identificador_sessao': 'teste-previa'
    }).status_code == 422

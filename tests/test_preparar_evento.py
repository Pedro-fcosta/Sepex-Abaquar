import sqlite3
from pathlib import Path

from app.db import conexao


LOTE = Path(__file__).resolve().parents[1] / 'Foguete Modular - Banco' / 'gerados' / 'csv'


def test_preparar_evento_exige_os_108_voos(app, tmp_path):
    backup = tmp_path / 'antes.sqlite3'
    resposta = app.test_cli_runner().invoke(args=['preparar-evento', str(backup)])
    assert resposta.exit_code != 0
    assert 'Apenas 0/108' in resposta.output
    assert not backup.exists()


def test_preparar_evento_guarda_historico_e_zera_placar(app, cliente, tmp_path, monkeypatch):
    importacao = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert importacao.exit_code == 0, importacao.output
    tentativa = cliente.post('/api/tentativas', json={
        'nome': 'Visitante de teste', 'codigo': 'C1-A1-F3-S1',
        'identificador_sessao': 'preparo-evento-01',
    })
    assert tentativa.status_code == 201
    backup = tmp_path / 'antes.sqlite3'
    resposta = app.test_cli_runner().invoke(args=['preparar-evento', str(backup)])
    assert resposta.exit_code == 0, resposta.output
    assert '1 tentativas removidas' in resposta.output
    with sqlite3.connect(backup) as antigo:
        assert antigo.execute('SELECT count(*) FROM tentativas').fetchone()[0] == 1
    with app.app_context():
        db = conexao()
        assert db.execute('SELECT count(*) FROM tentativas').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM participantes').fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM simulacoes WHERE status='approved'").fetchone()[0] == 108
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert cliente.get('/api/ranking/placar').json['linhas'] == []
    assert '108 / 108' in cliente.get('/diagnostico').get_data(as_text=True)
    assert app.test_cli_runner().invoke(args=['preparar-evento', str(backup)]).exit_code != 0
    monkeypatch.setenv('SEPEX_SECRET_KEY', 'chave-de-operacao-do-teste')
    prontidao = app.test_cli_runner().invoke(args=['verificar-prontidao'])
    assert prontidao.exit_code == 0, prontidao.output
    assert '108/108 ORKs, CSVs e gráficos íntegros' in prontidao.output

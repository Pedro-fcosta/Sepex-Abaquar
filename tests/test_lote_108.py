from pathlib import Path

from app.db import conexao


LOTE = Path(__file__).resolve().parents[1] / 'Foguete Modular - Banco' / 'gerados' / 'csv'


def test_lote_gerado_libera_108_graficos(app, cliente):
    importacao = app.test_cli_runner().invoke(args=['importar-lote', str(LOTE)])
    assert importacao.exit_code == 0, importacao.output
    assert '108 importadas' in importacao.output

    with app.app_context():
        codigos = [r[0] for r in conexao().execute('SELECT codigo FROM configuracoes ORDER BY codigo')]
        assert len(codigos) == 108
        assert conexao().execute("SELECT count(*) FROM simulacoes WHERE status='approved'").fetchone()[0] == 108

    for codigo in codigos:
        resposta = cliente.get(f'/api/previa/{codigo}')
        assert resposta.status_code == 200, codigo
        assert len(resposta.json['pontos']) >= 10, codigo
        assert resposta.json['origem_trajetoria'] == 'serie_openrocket'

    codigo_parcial = 'C2-A1-F3-S1'
    assert 'Resultado parcial' in cliente.get(f'/previa/{codigo_parcial}').get_data(as_text=True)
    tentativa = cliente.post('/api/tentativas', json={
        'nome': 'Teste parcial', 'codigo': codigo_parcial,
        'identificador_sessao': 'lote-108-parcial',
    })
    assert tentativa.status_code == 201
    assert 'Resultado parcial' in cliente.get(tentativa.json['url_voo']).get_data(as_text=True)
    assert 'resultado parcial' in cliente.get(f'/resultado/{tentativa.json["id"]}').get_data(as_text=True)

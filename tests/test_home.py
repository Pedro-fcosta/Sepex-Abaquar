from app import criar_app
from app.simulacoes import importar
from app.tentativas import registrar


def test_home_sem_banco_inicializado(tmp_path):
    app = criar_app({'TESTING': True, 'DATABASE': str(tmp_path / 'vazio.sqlite3')})
    pagina = app.test_client().get('/')
    assert pagina.status_code == 200
    html = pagina.get_data(as_text=True)
    assert '0 configurações carregadas' in html
    assert 'O ranking será preenchido durante a SEPEX.' in html


def test_home_mostra_somente_tres_primeiras_tentativas_reais(app, cliente):
    codigos = ['C1-A1-F3-S1', 'C1-A1-F3-S2', 'C1-A1-F3-S3', 'C1-A1-F3-S4']
    with app.app_context():
        for indice, codigo in enumerate(codigos):
            conteudo = f'Apogee (m),Maximum velocity (m/s)\n{100 + indice * 10},40\n'.encode()
            importar(conteudo, f'{codigo}.csv', codigo)
            registrar(f'Real {indice}', codigo, f'home-real-000{indice}')
    resultado = app.test_cli_runner().invoke(args=['demo-criar'])
    assert resultado.exit_code == 0, resultado.output
    with app.app_context():
        registrar('Visita Demo', 'C2-A3-F4-S2', 'home-demo-0000')

    html = cliente.get('/').get_data(as_text=True)
    assert '108 configurações carregadas' in html
    for nome in ('Real 3', 'Real 2', 'Real 1'):
        assert nome in html
    assert 'Real 0' not in html
    assert 'Visita Demo' not in html
    assert 'O ranking será preenchido durante a SEPEX.' not in html

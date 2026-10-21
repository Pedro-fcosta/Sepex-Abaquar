import csv
import io

from app.db import conexao
from app.simulacoes import importar, revisar
from app.web import csv_tentativas


def _simulacao(app, codigo, margem):
    with app.app_context():
        conteudo = f'Apogee (m),Maximum velocity (m/s),Maximum acceleration (m/s2)\n100,40,70\n'.encode()
        identificador, _ = importar(conteudo, f'{codigo}.csv', codigo)
        revisar(identificador, 'approved')
        with conexao():
            conexao().execute('UPDATE simulacoes SET margem_calibres=? WHERE id=?', (margem, identificador))


def test_limiar_05_classificacao_dashboard_e_exportacao(app, cliente):
    inseguro = 'C1-A1-F3-S1'
    limite = 'C1-A1-F3-S2'
    _simulacao(app, inseguro, 0.49)
    _simulacao(app, limite, 0.5)
    respostas = [cliente.post('/api/tentativas', json={
        'nome': nome, 'codigo': codigo, 'identificador_sessao': sessao,
    }) for nome, codigo, sessao in (
        ('Teste inseguro', inseguro, 'teste-inseguro-123'),
        ('Teste limite', limite, 'teste-limite-12345'),
    )]
    assert all(resposta.status_code == 201 for resposta in respostas)
    id_inseguro, id_limite = (resposta.json['id'] for resposta in respostas)
    with app.app_context():
        with conexao():
            conexao().execute('UPDATE tentativas SET posicao_calculada=1 WHERE id=?', (id_inseguro,))

    assert cliente.get(f'/api/voo/{id_inseguro}').json['tentativa']['abortada'] is True
    assert cliente.get(f'/api/voo/{id_inseguro}').json['tentativa']['posicao_calculada'] is None
    assert cliente.get(f'/api/voo/{id_limite}').json['tentativa']['abortada'] is False
    assert 'MISSÃO ABORTADA' in cliente.get(f'/resultado/{id_inseguro}').get_data(as_text=True)
    assert 'Posição atual no ranking' not in cliente.get(f'/resultado/{id_inseguro}').get_data(as_text=True)
    assert 'MISSÃO CONCLUÍDA' in cliente.get(f'/resultado/{id_limite}').get_data(as_text=True)
    assert [linha['id'] for linha in cliente.get('/api/ranking').json] == [id_limite]

    resumo = cliente.get('/api/dashboard/resumo').json
    assert (resumo['total_tentativas'], resumo['voos_validos'], resumo['missoes_abortadas']) == (2, 1, 1)
    assert resumo['apogeu_medio_m'] == 100
    assert sum(cliente.get('/api/dashboard/distribuicoes').json['apogeu']['contagens']) == 1
    with app.app_context():
        linhas = list(csv.DictReader(io.StringIO(csv_tentativas().lstrip('\ufeff'))))
    assert [linha['posicao_calculada'] for linha in linhas] == ['', '1']
    assert [linha['estado_missao'] for linha in linhas] == ['abortada', 'classificada']


def test_dashboard_so_com_abortada(app, cliente):
    codigo = 'C1-A1-F3-S1'
    _simulacao(app, codigo, 0.0)
    resposta = cliente.post('/api/tentativas', json={
        'nome': 'Teste aborto', 'codigo': codigo, 'identificador_sessao': 'teste-aborto-1234',
    })
    assert resposta.status_code == 201
    pagina = cliente.get('/dashboard').get_data(as_text=True)
    assert 'Aguardando uma missão classificada' in pagina
    assert 'grafico-tempo' in pagina
    assert 'grafico-apogeu' not in pagina
    assert cliente.get('/api/ranking/placar').json['linhas'] == []


def test_admin_local_only_restringe_dispositivos_remotos(app, cliente):
    app.config['ADMIN_LOCAL_ONLY'] = True
    remoto = {'REMOTE_ADDR': '203.0.113.7'}
    assert cliente.get('/').status_code == 200
    assert cliente.get('/admin/entrar', environ_overrides=remoto).status_code == 403
    assert cliente.get('/admin/exportar', headers={'X-Admin-Token': 'token-teste'}, environ_overrides=remoto).status_code == 403
    assert cliente.get('/admin/entrar', environ_overrides={'REMOTE_ADDR': '127.0.0.1'}).status_code == 200
    assert cliente.get('/admin/exportar', headers={'X-Admin-Token': 'token-teste'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}).status_code == 200
